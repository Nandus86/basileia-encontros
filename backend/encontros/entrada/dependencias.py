"""O que as rotas recebem prontas: o container, a pessoa do token e a conferência da chave do líder."""
from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request

from encontros.container import Container
from encontros.dominio.perfil import Perfil


def container(request: Request) -> Container:
    return request.app.state.c


async def eu(request: Request, c: Container = Depends(container)) -> Perfil:
    cabecalho = request.headers.get("authorization", "")
    pessoa_id = c.tokens.pessoa_do_acesso(cabecalho[7:]) if cabecalho.lower().startswith("bearer ") else None
    pessoa = await c.repositorio.perfil(pessoa_id) if pessoa_id else None
    if not pessoa or not pessoa.elegivel:
        raise HTTPException(401, "Entre de novo.")
    return pessoa


async def lider(request: Request, c: Container = Depends(container)) -> None:
    """Painel do líder: a chave vai no cabeçalho X-Chave-Lider. Sem chave configurada, o painel fica desligado."""
    if not c.chave_lider:
        raise HTTPException(404)
    if not hmac.compare_digest(request.headers.get("x-chave-lider", ""), c.chave_lider):
        raise HTTPException(401, "Chave do líder incorreta.")
