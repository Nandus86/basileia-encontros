"""Conteúdo do app (devocionais, perguntas a dois, testes): a IA escreve, o líder aprova.

Nada gerado pela IA aparece para os membros antes da aprovação. Os testes são de visão e vivência
(as opções vão de um extremo ao outro), nunca de certo e errado: o app não dá nota para a fé de ninguém.
"""
from __future__ import annotations

import logging
from typing import List, Mapping, Optional

from encontros.aplicacao.portas import Conteudo, Escritor, Repositorio

logger = logging.getLogger(__name__)

TIPOS = ("devocional", "pergunta", "teste")
MAXIMO_POR_VEZ = 5

REGRAS_GERAIS = (
    "Você escreve conteúdo para um app cristão evangélico de amizade e relacionamento entre membros solteiros de "
    "várias igrejas (denominações diferentes). Português do Brasil, linguagem simples e calorosa. "
    "Evite temas que dividem denominações (batismo, dons, escatologia, liturgia, política). "
    "NÃO transcreva versículos: cite só a referência (ex.: Salmos 23:1-3), para a pessoa ler na própria Bíblia. "
    "Nada de conteúdo romântico ou sensual; o foco é fé, caráter, valores e vida em comunidade. "
    "Responda APENAS com JSON válido no formato pedido.")

INSTRUCOES = {
    "devocional": (
        'Escreva {n} devocional(is) curto(s). Formato: {{"itens": [{{"titulo": "até 60 letras", '
        '"referencia": "Livro cap:vers", "reflexao": "reflexão original de 60 a 120 palavras", '
        '"pergunta": "uma pergunta pessoal para a pessoa responder em uma ou duas frases"}}]}}'),
    "pergunta": (
        'Escreva {n} pergunta(s) para duas pessoas responderem separadas e depois verem a resposta uma da outra. '
        'Devem revelar visão de fé, valores e jeito de viver, sem ser íntimas demais. '
        'Formato: {{"itens": [{{"texto": "a pergunta, até 140 letras"}}]}}'),
    "teste": (
        'Crie {n} teste(s) de visão e vivência cristã, com 5 questões cada. Cada questão tem exatamente 4 opções '
        'em ESCALA DE ESTILO, de um extremo ao outro (a 1ª e a 4ª opostas, a 2ª e a 3ª no meio): por exemplo, mais '
        'reservado ↔ mais expansivo, mais planejado ↔ mais espontâneo, mais a sós ↔ mais em grupo. TODAS as opções '
        'devem ser jeitos legítimos e respeitáveis de um cristão viver; nenhuma pode soar mais madura, mais santa ou '
        'mais correta que a outra (nada de "guardo mágoa" contra "perdoo logo"). '
        'Formato: {{"itens": [{{"titulo": "até 50 letras", "tema": "uma palavra", "questoes": '
        '[{{"texto": "a questão", "opcoes": ["…", "…", "…", "…"]}}]}}]}}'),
}


class ConteudoInvalido(ValueError):
    pass


def _texto(valor, minimo: int, maximo: int, nome: str) -> str:
    texto = " ".join(str(valor or "").split())
    if not (minimo <= len(texto) <= maximo):
        raise ConteudoInvalido(f"'{nome}' precisa ter entre {minimo} e {maximo} letras.")
    return texto


def validar(tipo: str, dados: Mapping) -> dict:
    if tipo == "devocional":
        return {"titulo": _texto(dados.get("titulo"), 3, 80, "título"),
                "referencia": _texto(dados.get("referencia"), 3, 40, "referência"),
                "reflexao": _texto(dados.get("reflexao"), 40, 1500, "reflexão"),
                "pergunta": _texto(dados.get("pergunta"), 10, 220, "pergunta")}
    if tipo == "pergunta":
        return {"texto": _texto(dados.get("texto"), 10, 220, "pergunta")}
    if tipo == "teste":
        questoes = dados.get("questoes") or []
        if not (3 <= len(questoes) <= 8):
            raise ConteudoInvalido("O teste precisa ter de 3 a 8 questões.")
        limpas = []
        for q in questoes:
            opcoes = [_texto(o, 1, 120, "opção") for o in (q.get("opcoes") or [])]
            if len(opcoes) != 4:
                raise ConteudoInvalido("Cada questão precisa de exatamente 4 opções.")
            limpas.append({"texto": _texto(q.get("texto"), 5, 200, "questão"), "opcoes": opcoes})
        return {"titulo": _texto(dados.get("titulo"), 3, 60, "título"),
                "tema": _texto(dados.get("tema") or "vida cristã", 2, 40, "tema"), "questoes": limpas}
    raise ConteudoInvalido("Tipo desconhecido.")


class Conteudos:
    def __init__(self, repositorio: Repositorio, escritor: Optional[Escritor]):
        self._repo = repositorio
        self._escritor = escritor

    async def lista(self, status: Optional[str] = None) -> List[Conteudo]:
        return await self._repo.conteudos(status=status)

    async def aprovar(self, conteudo_id: int, dados: Optional[Mapping] = None) -> Conteudo:
        atual = await self._repo.conteudo(conteudo_id)
        if not atual:
            raise LookupError()
        limpos = validar(atual.tipo, dados if dados is not None else atual.dados)
        return await self._repo.decidir_conteudo(conteudo_id, "aprovado", limpos)

    async def recusar(self, conteudo_id: int) -> Conteudo:
        feito = await self._repo.decidir_conteudo(conteudo_id, "recusado")
        if not feito:
            raise LookupError()
        return feito

    async def criar(self, tipo: str, dados: Mapping) -> Conteudo:
        """O líder também pode escrever o próprio conteúdo (já sai aprovado)."""
        return await self._repo.salvar_conteudo(tipo, validar(tipo, dados), "aprovado", "lider")

    async def gerar(self, tipo: str, quantidade: int = 3) -> List[Conteudo]:
        if tipo not in TIPOS:
            raise ConteudoInvalido("Tipo desconhecido.")
        if self._escritor is None:
            raise ConteudoInvalido("A IA não está configurada (falta a chave da OpenRouter).")
        quantidade = max(1, min(MAXIMO_POR_VEZ, quantidade))
        existentes = [c.titulo for c in await self._repo.conteudos(tipo=tipo)][-40:]
        pedido = INSTRUCOES[tipo].format(n=quantidade)
        if existentes:
            pedido += "\nNão repita estes, que já existem: " + "; ".join(existentes)
        resposta = await self._escritor.escrever(REGRAS_GERAIS, pedido)
        novos = []
        for item in (resposta.get("itens") or [])[:quantidade]:
            try:
                novos.append(await self._repo.salvar_conteudo(tipo, validar(tipo, item), "pendente", "ia"))
            except ConteudoInvalido as erro:
                logger.warning("[encontros] conteúdo da IA descartado (%s)", erro)
        if not novos:
            raise ConteudoInvalido("A IA não devolveu nada aproveitável. Tente de novo.")
        return novos
