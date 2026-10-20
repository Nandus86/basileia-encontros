"""Casos de uso do mistério: sinais do dia, conexões, revelações, pergunta a dois e chat.

- Sinais do dia: poucos por dia (3 a 5, conforme o nível da jornada), escolhidos uma vez e guardados;
- Conexão: os dois enviaram sinal. Começa com pontos pela afinidade de hobbies e localização;
- Revelações: cada pessoa escolhe com quantos pontos revela cada coisa (ou libera na mão);
- Chat: só quando os dois revelaram o chat (vale o maior dos limites).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from encontros.aplicacao.curadoria import Curadoria, Sugestao
from encontros.aplicacao.jornada import NaoEncontrado, Recusado, limpar_texto
from encontros.aplicacao.pontuacao import Pontuacao, referencia
from encontros.aplicacao.portas import (Bots, Conexao, Conteudo, EventoDaDupla, Mensagem, Repositorio, Resposta,
                                        SinalDoDia)
from encontros.dominio.afinidade import Afinidade
from encontros.dominio.jornada import (ITENS, PONTOS_INICIAIS, PONTOS_PERGUNTA_A_DOIS, SINTONIA_INICIAL,
                                       SINTONIA_PARA_VER_NIVEL, TEMAS_CURTOS, chat_aberto, chat_abre_em, hoje,
                                       limiares, nivel_de, revelou, semelhanca_das_escolhas, semelhanca_dos_temas)
from encontros.dominio.perfil import Perfil

TAMANHO_DA_MENSAGEM = 1000
PESO_DO_NIVEL = {"alta": 1.0, "media": 0.7, "baixa": 0.4}


@dataclass(frozen=True)
class Sinal:
    pessoa: Perfil
    motivos: Tuple[str, ...]
    afinidade: Optional[Afinidade]


@dataclass(frozen=True)
class Revelacao:
    item: str
    rotulo: str
    limite: Optional[int]
    revelado: bool
    na_mao: bool


@dataclass(frozen=True)
class VisaoDaConexao:
    conexao: Conexao
    outra: Perfil
    dela: Dict[str, bool]                     # o que a outra pessoa já revelou para mim
    minhas: List[Revelacao]                   # o que eu revelo, e com quantos pontos
    chat_aberto: bool
    chat_abre_em: Optional[int]
    proxima_descoberta: Optional[Tuple[str, int]]   # o próximo item que ela revela, e em quantos pontos
    nivel_dela: Optional[str]                 # só com sintonia de 85% ou mais


@dataclass(frozen=True)
class PerguntaRespondida:
    conteudo: Conteudo
    minha: Resposta
    dela: Resposta


@dataclass(frozen=True)
class PerguntaDaVez:
    conteudo: Optional[Conteudo]
    minha: Optional[Resposta]
    dela: Optional[Resposta]                  # só aparece depois que eu respondo
    volta_amanha: bool = False
    anterior: Optional[PerguntaRespondida] = None   # a última que os dois responderam (para ver a resposta dela)


class Conexoes:
    def __init__(self, repositorio: Repositorio, curadoria: Curadoria, pontuacao: Pontuacao,
                 bots: Optional[Bots] = None, demo: bool = False):
        self._repo = repositorio
        self._curadoria = curadoria
        self._pontuacao = pontuacao
        self._bots = bots
        self._demo = demo

    # ---------------- sinais do dia ----------------

    async def sinais(self, pessoa: Perfil) -> List[Sinal]:
        if not (pessoa.completo and pessoa.visivel and pessoa.elegivel):
            return []
        dia = hoje().isoformat()
        guardados = await self._repo.sinais_do_dia(pessoa.id, dia)
        if guardados is None:
            feed = await self._curadoria.feed(pessoa)
            escolhidos = (await self._aprofundar(pessoa, feed))[:nivel_de(pessoa.jornada).sinais_por_dia]
            guardados = [SinalDoDia(s.pessoa.id, motivos) for s, motivos in escolhidos]
            await self._repo.guardar_sinais_do_dia(pessoa.id, dia, guardados)
        reagidos = await self._repo.reagidos_por(pessoa.id)
        pendentes = [g for g in guardados if g.outro_id not in reagidos]
        perfis = await self._repo.perfis([g.outro_id for g in pendentes])
        afinidades = await self._repo.afinidades(pessoa.id, list(perfis))
        return [Sinal(perfis[g.outro_id], g.motivos, (afinidades.get(g.outro_id) or (None, None))[1])
                for g in pendentes if g.outro_id in perfis and perfis[g.outro_id].elegivel]

    async def mais_sinais(self, pessoa: Perfil) -> None:
        """Só no modo de teste: escolhe os sinais de hoje de novo, sem esperar amanhã."""
        if not self._demo:
            raise Recusado("Novos sinais chegam amanhã.")
        await self._repo.esquecer_sinais_do_dia(pessoa.id, hoje().isoformat())

    async def responder_sinal(self, pessoa: Perfil, outra_id: int, enviar: bool) -> Optional[Conexao]:
        guardados = await self._repo.sinais_do_dia(pessoa.id, hoje().isoformat()) or []
        outra = await self._repo.perfil(outra_id)
        if outra_id not in {g.outro_id for g in guardados} or not outra:
            raise NaoEncontrado()
        conexao = await self._repo.reagir(pessoa.id, outra.id, enviar)
        if enviar and not conexao and self._bots and outra.demo:
            await self._bots.ao_enviar_sinal(pessoa, outra)
            conexao = await self._repo.conexao_entre(pessoa.id, outra.id)
        if conexao:
            await self.iniciar(conexao, pessoa, outra)
            conexao = await self._repo.conexao(conexao.id)
        return conexao

    async def iniciar(self, conexao: Conexao, a: Perfil, b: Perfil, pontos: Optional[int] = None) -> None:
        """Os primeiros pontos vêm da afinidade; e tudo que os dois já responderam em comum conta na hora."""
        afinidade = await self._curadoria.afinidade(a, b)
        nivel = afinidade.nivel.value if afinidade else "media"
        await self._repo.registrar_evento(conexao.id, "inicio", EventoDaDupla(
            "inicio", "Vocês se conectaram", pontos if pontos is not None else PONTOS_INICIAIS[nivel],
            SINTONIA_INICIAL[nivel]))
        respostas = await self._repo.respostas([a.id, b.id])
        de_a = {r.conteudo_id for r in respostas if r.pessoa_id == a.id}
        em_comum = de_a & {r.conteudo_id for r in respostas if r.pessoa_id == b.id}
        for conteudo_id in sorted(em_comum):
            conteudo = await self._repo.conteudo(conteudo_id)
            if conteudo and conteudo.tipo in ("teste", "devocional"):
                await self._pontuacao.pontuar(conexao, conteudo)

    async def _aprofundar(self, pessoa: Perfil, feed: Sequence[Sugestao]) -> List[Tuple[Sugestao, Tuple[str, ...]]]:
        """A análise fica mais funda com o que a pessoa já respondeu: testes em comum (valores) e temas dos
        devocionais entram na ordem e nos motivos, além dos hobbies."""
        if not feed:
            return []
        respostas = await self._repo.respostas([pessoa.id] + [s.pessoa.id for s in feed])
        por_pessoa: Dict[int, Dict[int, Resposta]] = {}
        for r in respostas:
            por_pessoa.setdefault(r.pessoa_id, {})[r.conteudo_id] = r
        testes = {c.id: c for c in await self._repo.conteudos("teste", "aprovado")}
        minhas = por_pessoa.get(pessoa.id, {})
        meus_temas = [t for r in minhas.values() for t in r.temas]

        pontuados = []
        for s in feed:
            dela = por_pessoa.get(s.pessoa.id, {})
            partes = [(PESO_DO_NIVEL[s.afinidade.nivel.value], 0.5)]
            motivos = []
            if s.afinidade.em_comum:
                motivos.append("Vocês dois curtem " + " e ".join(h.lower() for h in s.afinidade.em_comum[:2]))
            comuns = [t for t in testes if t in minhas and t in dela]
            if comuns:
                semelhancas = {t: semelhanca_das_escolhas(minhas[t].dados.get("escolhas") or [],
                                                          dela[t].dados.get("escolhas") or []) for t in comuns}
                partes.append((sum(semelhancas.values()) / len(semelhancas), 0.3))
                melhor = max(semelhancas, key=semelhancas.get)
                if semelhancas[melhor] >= 0.75:
                    motivos.append(f"Responderam parecido em “{testes[melhor].titulo}”")
            temas_dela = [t for r in dela.values() for t in r.temas]
            if meus_temas and temas_dela:
                partes.append((semelhanca_dos_temas(meus_temas, temas_dela), 0.2))
                juntos = [t for t in dict.fromkeys(meus_temas) if t in set(temas_dela)]
                if juntos:
                    motivos.append(f"Os dois escreveram sobre {TEMAS_CURTOS.get(juntos[0], juntos[0])}")
            nota = sum(v * p for v, p in partes) / sum(p for _, p in partes)
            pontuados.append((nota, s, tuple(motivos) or ("Interesses que se completam",)))
        pontuados.sort(key=lambda x: -x[0])
        return [(s, motivos) for _, s, motivos in pontuados]

    # ---------------- conexões e revelações ----------------

    async def conexao_de(self, pessoa: Perfil, conexao_id: int) -> Tuple[Conexao, Perfil]:
        conexao = await self._repo.conexao(conexao_id)
        if not conexao or not conexao.tem(pessoa.id) or conexao.desfeita:
            raise NaoEncontrado()
        outra = await self._repo.perfil(conexao.outra(pessoa.id))
        if not outra or not outra.elegivel:
            raise NaoEncontrado()
        return conexao, outra

    def visao(self, conexao: Conexao, eu: Perfil, outra: Perfil) -> VisaoDaConexao:
        meus, dela = limiares(eu.revelacoes), limiares(outra.revelacoes)
        meus_na_mao, dela_na_mao = conexao.liberados.get(eu.id, frozenset()), conexao.liberados.get(outra.id, frozenset())
        pontos = conexao.pontos
        revelado_dela = {item: revelou(item, dela, dela_na_mao, pontos) for item, _ in ITENS}
        minhas = [Revelacao(item, rotulo, meus[item], revelou(item, meus, meus_na_mao, pontos), item in meus_na_mao)
                  for item, rotulo in ITENS]
        proximas = sorted((dela[item], rotulo) for item, rotulo in ITENS
                          if not revelado_dela[item] and dela[item] is not None and item != "chat")
        sintonia = conexao.sintonia or 0
        return VisaoDaConexao(
            conexao=conexao, outra=outra, dela=revelado_dela, minhas=minhas,
            chat_aberto=chat_aberto(meus, meus_na_mao, dela, dela_na_mao, pontos),
            chat_abre_em=chat_abre_em(meus, meus_na_mao, dela, dela_na_mao),
            proxima_descoberta=(proximas[0][1], proximas[0][0]) if proximas else None,
            nivel_dela=nivel_de(outra.jornada).nome if sintonia >= SINTONIA_PARA_VER_NIVEL else None)

    async def liberar(self, pessoa: Perfil, conexao_id: int, item: str) -> None:
        if item not in dict(ITENS):
            raise Recusado("Item desconhecido.")
        conexao, _ = await self.conexao_de(pessoa, conexao_id)
        await self._repo.liberar(conexao.id, pessoa.id, item)

    async def pode_ver_foto(self, espectador_id: int, dono_id: int) -> bool:
        if espectador_id == dono_id:
            return True
        conexao = await self._repo.conexao_entre(espectador_id, dono_id)
        if not conexao or conexao.desfeita:
            return False
        dono = await self._repo.perfil(dono_id)
        return bool(dono) and revelou("foto", limiares(dono.revelacoes), conexao.liberados.get(dono_id, ()),
                                      conexao.pontos)

    # ---------------- pergunta a dois ----------------

    async def pergunta_da_vez(self, conexao: Conexao, eu: Perfil) -> PerguntaDaVez:
        """A primeira pergunta aprovada que a dupla ainda não pontuou. Uma por dia (no modo de teste, sem limite)."""
        perguntas = await self._repo.conteudos("pergunta", "aprovado")
        feitas = await self._repo.referencias(conexao.id)
        da_vez = next((p for p in perguntas if referencia(p) not in feitas), None)
        ultima = next((p for p in reversed(perguntas) if referencia(p) in feitas), None)
        ela = conexao.outra(eu.id)
        ids = [p.id for p in (da_vez, ultima) if p]
        respostas = {(r.pessoa_id, r.conteudo_id): r for r in await self._repo.respostas([eu.id, ela], ids)}
        anterior = None
        if ultima and (eu.id, ultima.id) in respostas and (ela, ultima.id) in respostas:
            anterior = PerguntaRespondida(ultima, respostas[(eu.id, ultima.id)], respostas[(ela, ultima.id)])
        if da_vez is None:
            return PerguntaDaVez(None, None, None, anterior=anterior)
        minha = respostas.get((eu.id, da_vez.id))
        if not minha and not self._demo and await self._repo.eventos_de_hoje(conexao.id, "pergunta", hoje().isoformat()):
            return PerguntaDaVez(None, None, None, volta_amanha=True, anterior=anterior)
        return PerguntaDaVez(da_vez, minha, respostas.get((ela, da_vez.id)) if minha else None, anterior=anterior)

    async def responder_pergunta(self, pessoa: Perfil, conexao_id: int, texto: str) -> Optional[EventoDaDupla]:
        conexao, outra = await self.conexao_de(pessoa, conexao_id)
        vez = await self.pergunta_da_vez(conexao, pessoa)
        if not vez.conteudo or vez.minha:
            raise Recusado("Essa pergunta já foi respondida.")
        if await self._repo.salvar_resposta(Resposta(pessoa.id, vez.conteudo.id, {"texto": limpar_texto(texto)})):
            await self._repo.somar_jornada(pessoa.id, PONTOS_PERGUNTA_A_DOIS)
        if self._bots and outra.demo:
            await self._bots.responder_se_preciso(outra, vez.conteudo)
        evento = None
        for c in await self._repo.conexoes_de(pessoa.id):     # a mesma resposta vale em todas as conexões
            feito = await self._pontuacao.pontuar(c, vez.conteudo)
            if c.id == conexao.id:
                evento = feito
        return evento

    # ---------------- chat ----------------

    async def _com_chat(self, pessoa: Perfil, conexao_id: int) -> Tuple[Conexao, Perfil]:
        conexao, outra = await self.conexao_de(pessoa, conexao_id)
        if not self.visao(conexao, pessoa, outra).chat_aberto:
            raise Recusado("O chat ainda não abriu para vocês.")
        return conexao, outra

    async def mensagens(self, pessoa: Perfil, conexao_id: int, depois_de: int = 0) -> List[Mensagem]:
        await self._com_chat(pessoa, conexao_id)
        return await self._repo.mensagens(conexao_id, depois_de)

    async def enviar(self, pessoa: Perfil, conexao_id: int, texto: str) -> Mensagem:
        conexao, outra = await self._com_chat(pessoa, conexao_id)
        texto = (texto or "").strip()
        if not texto:
            raise Recusado("Escreva uma mensagem.")
        if len(texto) > TAMANHO_DA_MENSAGEM:
            raise Recusado(f"A mensagem pode ter até {TAMANHO_DA_MENSAGEM} letras.")
        mensagem = await self._repo.enviar(conexao.id, pessoa.id, texto)
        if self._bots and outra.demo:
            await self._bots.ao_receber_mensagem(conexao, outra)
        return mensagem
