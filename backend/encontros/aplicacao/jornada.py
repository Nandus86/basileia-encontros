"""Casos de uso da jornada pessoal: devocional do dia e testes. Cada resposta também pontua as conexões
em que a outra pessoa já respondeu a mesma coisa."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Sequence, Tuple

from encontros.aplicacao.pontuacao import Pontuacao
from encontros.aplicacao.comparador import Comparador
from encontros.aplicacao.portas import Bots, Conteudo, Repositorio, Resposta
from encontros.dominio.jornada import (PONTOS_TESTE, Nivel, hoje, nivel_de, nova_sequencia, pontos_do_devocional,
                                       profundidade)
from encontros.dominio.perfil import Perfil, bio_tem_contato

TAMANHO_DA_RESPOSTA = 1000


class Recusado(ValueError):
    pass


class NaoEncontrado(LookupError):
    pass


def limpar_texto(texto: str) -> str:
    texto = " ".join((texto or "").split())
    if len(texto) < 3:
        raise Recusado("Escreva um pouco mais.")
    if len(texto) > TAMANHO_DA_RESPOSTA:
        raise Recusado(f"Pode ter até {TAMANHO_DA_RESPOSTA} letras.")
    if bio_tem_contato(texto):
        raise Recusado("Sem telefone, @ ou links: isso só depois que o chat abrir.")
    return texto


@dataclass(frozen=True)
class ResumoDaJornada:
    pontos: int
    nivel: Nivel
    sequencia: int
    profundidade: int
    devocional_hoje: bool
    testes_feitos: int


class Jornada:
    def __init__(self, repositorio: Repositorio, comparador: Comparador, pontuacao: Pontuacao,
                 bots: Optional[Bots] = None):
        self._repo = repositorio
        self._comparador = comparador
        self._pontuacao = pontuacao
        self._bots = bots

    async def resumo(self, pessoa: Perfil) -> ResumoDaJornada:
        contagem = await self._repo.contagem_de_respostas(pessoa.id)
        # a sequência só vale se o último devocional foi hoje ou ontem
        ultimo = date.fromisoformat(pessoa.ultimo_devocional) if pessoa.ultimo_devocional else None
        seguida = pessoa.sequencia if ultimo and (hoje() - ultimo).days <= 1 else 0
        return ResumoDaJornada(
            pontos=pessoa.jornada, nivel=nivel_de(pessoa.jornada), sequencia=seguida,
            profundidade=profundidade(contagem.get("teste", 0), contagem.get("devocional", 0), contagem.get("pergunta", 0)),
            devocional_hoje=pessoa.ultimo_devocional == hoje().isoformat(), testes_feitos=contagem.get("teste", 0))

    async def devocional_de_hoje(self) -> Optional[Conteudo]:
        """O mesmo para todo mundo no dia: o já marcado para hoje, senão o aprovado mais antigo que ainda não saiu
        (acabando, recomeça pelo que saiu há mais tempo)."""
        dia = hoje().isoformat()
        aprovados = await self._repo.conteudos("devocional", "aprovado")
        if not aprovados:
            return None
        de_hoje = next((c for c in aprovados if c.dia == dia), None)
        if de_hoje:
            return de_hoje
        livres = [c for c in aprovados if not c.dia]
        escolhido = livres[0] if livres else min(aprovados, key=lambda c: c.dia or "")
        await self._repo.marcar_dia(escolhido.id, dia)
        return await self._repo.conteudo(escolhido.id)

    async def responder_devocional(self, pessoa: Perfil, texto: str) -> int:
        devocional = await self.devocional_de_hoje()
        if not devocional:
            raise NaoEncontrado()
        texto = limpar_texto(texto)
        temas = await self._comparador.temas(texto)
        if not await self._repo.salvar_resposta(Resposta(pessoa.id, devocional.id, {"texto": texto}, temas)):
            raise Recusado("Você já fez o devocional de hoje. Volte amanhã!")
        dia = hoje()
        sequencia = nova_sequencia(pessoa.ultimo_devocional, dia, pessoa.sequencia)
        ganho = pontos_do_devocional(sequencia)
        await self._repo.somar_jornada(pessoa.id, ganho, sequencia=sequencia, ultimo_devocional=dia.isoformat())
        await self.pontuar_conexoes(pessoa, devocional)
        return ganho

    async def testes(self, pessoa: Perfil) -> List[Tuple[Conteudo, bool]]:
        testes = await self._repo.conteudos("teste", "aprovado")
        feitos = {r.conteudo_id for r in await self._repo.respostas([pessoa.id], [t.id for t in testes])}
        return [(t, t.id in feitos) for t in testes]

    async def teste(self, teste_id: int) -> Conteudo:
        teste = await self._repo.conteudo(teste_id)
        if not teste or teste.tipo != "teste" or teste.status != "aprovado":
            raise NaoEncontrado()
        return teste

    async def responder_teste(self, pessoa: Perfil, teste_id: int, escolhas: Sequence[int]) -> int:
        teste = await self.teste(teste_id)
        questoes = teste.dados.get("questoes") or []
        if len(escolhas) != len(questoes) or any(e not in range(len(q["opcoes"])) for e, q in zip(escolhas, questoes)):
            raise Recusado("Responda todas as perguntas.")
        if not await self._repo.salvar_resposta(Resposta(pessoa.id, teste.id, {"escolhas": list(escolhas)})):
            raise Recusado("Você já fez esse teste.")
        await self._repo.somar_jornada(pessoa.id, PONTOS_TESTE)
        await self.pontuar_conexoes(pessoa, teste)
        return PONTOS_TESTE

    async def pontuar_conexoes(self, pessoa: Perfil, conteudo: Conteudo) -> None:
        conexoes = await self._repo.conexoes_de(pessoa.id)
        if self._bots:
            outras = await self._repo.perfis([c.outra(pessoa.id) for c in conexoes])
            for outra in outras.values():
                if outra.demo:
                    await self._bots.responder_se_preciso(outra, conteudo)
        for conexao in conexoes:
            await self._pontuacao.pontuar(conexao, conteudo)
