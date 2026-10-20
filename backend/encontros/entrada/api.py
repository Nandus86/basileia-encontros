"""API do app (FastAPI). Tudo, menos /entrar, /hobbies e /saude, exige o token no cabeçalho Authorization;
o /lider exige a chave do líder (X-Chave-Lider)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Awaitable, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from encontros.config import Configuracao, configuracao
from encontros.container import Container, montar
from encontros.entrada import rotas_conexoes, rotas_jornada, rotas_lider, rotas_perfil


def criar_app(montador: Callable[[Configuracao], Awaitable[Container]] = montar,
              config: Optional[Configuracao] = None) -> FastAPI:
    config = config or configuracao()

    @asynccontextmanager
    async def ciclo(app: FastAPI):
        app.state.c = await montador(config)
        yield
        await app.state.c.fechar()

    app = FastAPI(title="Basiléia Encontros", version="0.0.2", lifespan=ciclo)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in config.origens.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["Authorization", "Content-Type", "X-Chave-Lider"])
    for modulo in (rotas_perfil, rotas_conexoes, rotas_jornada, rotas_lider):
        app.include_router(modulo.rotas)
    return app
