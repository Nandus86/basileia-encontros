"""Compara respostas abertas e tira os temas do que a pessoa escreveu (JEV; sem IA, por palavras)."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from encontros.aplicacao.julgamentos import PERGUNTA_COMPARAR, PERGUNTA_TEMA
from encontros.aplicacao.portas import Julgador
from encontros.dominio.jornada import comparacao_por_palavras, temas_por_palavras

logger = logging.getLogger(__name__)


class Comparador:
    def __init__(self, julgador: Optional[Julgador]):
        self._julgador = julgador

    async def comparar(self, pergunta: str, resposta_a: str, resposta_b: str) -> str:
        """muito_parecidas, parecidas, complementares ou diferentes."""
        if self._julgador is not None:
            estado = f"Pergunta: {pergunta}\nResposta da pessoa A: {resposta_a}\nResposta da pessoa B: {resposta_b}"
            try:
                return (await self._julgador.julgar(estado, {"comparacao": PERGUNTA_COMPARAR})).respostas["comparacao"]
            except Exception as erro:
                logger.warning("[encontros] comparação pela IA indisponível (%s)", str(erro)[:150])
        return comparacao_por_palavras(resposta_a, resposta_b)

    async def temas(self, texto: str) -> Tuple[str, ...]:
        if self._julgador is not None and len(texto.split()) >= 4:
            try:
                return ((await self._julgador.julgar(f"Texto: {texto}", {"tema": PERGUNTA_TEMA})).respostas["tema"],)
            except Exception as erro:
                logger.warning("[encontros] temas pela IA indisponíveis (%s)", str(erro)[:150])
        return temas_por_palavras(texto)
