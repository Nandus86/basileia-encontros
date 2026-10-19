"""Curadoria: quem aparece para a pessoa em "Descobrir". Grafo do LangGraph:

    buscar_candidatos → separar_conhecidas → [julgar → guardar] → montar_feed

- buscar_candidatos: regras duras (gênero, idade que cada um aceita, distância) — sem IA;
- separar_conhecidas: a afinidade de cada par fica guardada; só volta a ser julgada se algum perfil mudou;
- julgar: o JEV responde as perguntas de afinidade (com a reserva por LLM e, por último, as regras);
- montar_feed: só os compatíveis ("as mesmas características"), os de mais afinidade primeiro.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import END, START, StateGraph

from encontros.aplicacao.julgamentos import PERGUNTAS_AFINIDADE, afinidade_das_respostas
from encontros.aplicacao.portas import Julgador, Repositorio
from encontros.dominio.afinidade import (ORDEM_DO_NIVEL, Afinidade, afinidade_por_regras, assinatura,
                                         descrever_para_o_julgador, distancia_entre, em_comum, podem_se_ver)
from encontros.dominio.perfil import Perfil

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sugestao:
    pessoa: Perfil
    afinidade: Afinidade
    distancia_km: Optional[float]


class EstadoDaCuradoria(TypedDict, total=False):
    pessoa: Perfil
    candidatos: List[Perfil]
    conhecidas: Dict[int, Afinidade]
    a_julgar: List[Perfil]
    novas: Dict[int, Tuple[str, Afinidade]]
    feed: List[Sugestao]


class Curadoria:
    CANDIDATOS_POR_VEZ = 300
    TAMANHO_DO_FEED = 20

    def __init__(self, repositorio: Repositorio, julgador: Optional[Julgador], julgar_por_vez: int = 12,
                 simultaneos: int = 4):
        self._repo = repositorio
        self._julgador = julgador
        self._julgar_por_vez = julgar_por_vez
        self._simultaneos = simultaneos
        grafo = StateGraph(EstadoDaCuradoria)
        grafo.add_node("buscar_candidatos", self._buscar_candidatos)
        grafo.add_node("separar_conhecidas", self._separar_conhecidas)
        grafo.add_node("julgar", self._julgar)
        grafo.add_node("guardar", self._guardar)
        grafo.add_node("montar_feed", self._montar_feed)
        grafo.add_edge(START, "buscar_candidatos")
        grafo.add_edge("buscar_candidatos", "separar_conhecidas")
        grafo.add_conditional_edges("separar_conhecidas", lambda e: "julgar" if e.get("a_julgar") else "montar_feed",
                                    ["julgar", "montar_feed"])
        grafo.add_edge("julgar", "guardar")
        grafo.add_edge("guardar", "montar_feed")
        grafo.add_edge("montar_feed", END)
        self._grafo = grafo.compile()

    async def feed(self, pessoa: Perfil) -> List[Sugestao]:
        final = await self._grafo.ainvoke({"pessoa": pessoa})
        return final.get("feed", [])

    async def afinidade(self, a: Perfil, b: Perfil) -> Optional[Afinidade]:
        """A afinidade guardada do par, se ainda vale (para conferir uma curtida)."""
        guardada = (await self._repo.afinidades(a.id, [b.id])).get(b.id)
        if guardada and guardada[0] == assinatura(a, b):
            return guardada[1]
        return None

    # ---------------- nós do grafo ----------------

    async def _buscar_candidatos(self, estado: EstadoDaCuradoria) -> EstadoDaCuradoria:
        pessoa = estado["pessoa"]
        if not (pessoa.completo and pessoa.visivel and pessoa.elegivel):
            return {"candidatos": []}
        achados = await self._repo.candidatos_para(pessoa, self.CANDIDATOS_POR_VEZ)
        return {"candidatos": [c for c in achados if podem_se_ver(pessoa, c)]}

    async def _separar_conhecidas(self, estado: EstadoDaCuradoria) -> EstadoDaCuradoria:
        pessoa, candidatos = estado["pessoa"], estado["candidatos"]
        guardadas = await self._repo.afinidades(pessoa.id, [c.id for c in candidatos])
        conhecidas, a_julgar = {}, []
        for c in candidatos:
            g = guardadas.get(c.id)
            if g and g[0] == assinatura(pessoa, c):
                conhecidas[c.id] = g[1]
            elif not em_comum(pessoa, c) and not (pessoa.bio and c.bio):
                # nenhum hobby igual e nada escrito para o JEV achar algo parecido: nem vale a chamada
                conhecidas[c.id] = afinidade_por_regras(pessoa, c)
            else:
                a_julgar.append(c)
        # os mais próximos primeiro; o resto fica para a próxima vez que a pessoa abrir o Descobrir
        a_julgar.sort(key=lambda c: (-len(em_comum(pessoa, c)), distancia_entre(pessoa, c) or 0))
        return {"conhecidas": conhecidas, "a_julgar": a_julgar[:self._julgar_por_vez]}

    async def _julgar(self, estado: EstadoDaCuradoria) -> EstadoDaCuradoria:
        pessoa = estado["pessoa"]
        limite = asyncio.Semaphore(self._simultaneos)

        async def um(c: Perfil) -> Tuple[int, Tuple[str, Afinidade]]:
            async with limite:
                return c.id, (assinatura(pessoa, c), await self._julgar_par(pessoa, c))

        return {"novas": dict(await asyncio.gather(*(um(c) for c in estado["a_julgar"])))}

    async def _guardar(self, estado: EstadoDaCuradoria) -> EstadoDaCuradoria:
        await self._repo.guardar_afinidades(estado["pessoa"].id, estado["novas"])
        return {}

    async def _montar_feed(self, estado: EstadoDaCuradoria) -> EstadoDaCuradoria:
        pessoa = estado["pessoa"]
        todas = dict(estado.get("conhecidas") or {})
        todas.update({i: a for i, (_, a) in (estado.get("novas") or {}).items()})
        sugestoes = [Sugestao(c, todas[c.id], distancia_entre(pessoa, c))
                     for c in estado.get("candidatos") or [] if c.id in todas and todas[c.id].compativel]
        sugestoes.sort(key=lambda s: (ORDEM_DO_NIVEL[s.afinidade.nivel], -len(s.afinidade.em_comum),
                                      s.distancia_km if s.distancia_km is not None else 999))
        return {"feed": sugestoes[:self.TAMANHO_DO_FEED]}

    async def _julgar_par(self, a: Perfil, b: Perfil) -> Afinidade:
        if self._julgador is not None:
            try:
                julgamento = await self._julgador.julgar(descrever_para_o_julgador(a, b), PERGUNTAS_AFINIDADE)
                return afinidade_das_respostas(julgamento.respostas, em_comum(a, b), julgamento.origem)
            except Exception as erro:
                logger.warning("[encontros] julgamento falhou (%s) — usando as regras", str(erro)[:150])
        return afinidade_por_regras(a, b)
