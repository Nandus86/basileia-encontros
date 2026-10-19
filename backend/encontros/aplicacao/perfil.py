"""Caso de uso: a pessoa completa ou muda o próprio perfil (hobbies, sobre, preferências)."""
from __future__ import annotations

import logging
from typing import Optional, Sequence

from encontros.aplicacao.julgamentos import MOTIVOS_BIO, PERGUNTAS_BIO
from encontros.aplicacao.portas import Julgador, Repositorio
from encontros.dominio.perfil import (HOBBIES_MINIMOS, IDADE_MINIMA, Perfil, bio_tem_contato, limpar_bio,
                                      limpar_hobbies)

logger = logging.getLogger(__name__)


class PerfilRecusado(ValueError):
    pass


class AtualizarPerfil:
    def __init__(self, repositorio: Repositorio, julgador: Optional[Julgador]):
        self._repo = repositorio
        self._julgador = julgador

    async def executar(self, pessoa: Perfil, hobbies: Optional[Sequence[str]] = None, bio: Optional[str] = None,
                       idade_min: Optional[int] = None, idade_max: Optional[int] = None,
                       raio_km: Optional[int] = None, visivel: Optional[bool] = None) -> Perfil:
        campos = {}
        if hobbies is not None:
            limpos = limpar_hobbies(hobbies)
            if len(limpos) < HOBBIES_MINIMOS:
                raise PerfilRecusado(f"Escolha pelo menos {HOBBIES_MINIMOS} hobbies.")
            campos["hobbies"] = limpos
        if bio is not None:
            texto = limpar_bio(bio)
            if texto != pessoa.bio:
                await self._moderar(texto)
            campos["bio"] = texto
        if idade_min is not None or idade_max is not None:
            minimo = max(IDADE_MINIMA, idade_min if idade_min is not None else pessoa.idade_min)
            maximo = min(99, idade_max if idade_max is not None else pessoa.idade_max)
            if minimo > maximo:
                raise PerfilRecusado("A idade mínima precisa ser menor que a máxima.")
            campos.update(idade_min=minimo, idade_max=maximo)
        if raio_km is not None:
            campos["raio_km"] = max(1, min(200, int(raio_km)))
        if visivel is not None:
            campos["visivel"] = bool(visivel)
        return await self._repo.atualizar_perfil(pessoa.id, **campos) if campos else pessoa

    async def _moderar(self, texto: str) -> None:
        """Regras primeiro (contato fora do app); o JEV olha o resto. Se a IA cair, o texto passa."""
        if not texto:
            return
        if bio_tem_contato(texto):
            raise PerfilRecusado(MOTIVOS_BIO["contato"])
        if self._julgador is None:
            return
        try:
            veredito = (await self._julgador.julgar(f"Texto 'sobre mim': {texto}", PERGUNTAS_BIO)).respostas["bio"]
        except Exception as erro:
            logger.warning("[encontros] moderação da bio indisponível (%s)", str(erro)[:150])
            return
        if veredito in MOTIVOS_BIO:
            raise PerfilRecusado(MOTIVOS_BIO[veredito])
