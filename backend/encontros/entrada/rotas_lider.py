"""Painel do líder: aprovar o que a IA gerou, escrever conteúdo próprio e ver as denúncias."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from encontros.aplicacao.conteudo import ConteudoInvalido
from encontros.container import Container
from encontros.entrada.dependencias import container, lider
from encontros.entrada.formatos import conteudo

rotas = APIRouter(prefix="/lider", dependencies=[Depends(lider)])


class PedidoDeConteudo(BaseModel):
    tipo: str = Field(max_length=12)
    dados: dict


class PedidoDeAprovacao(BaseModel):
    dados: Optional[dict] = None          # o líder pode corrigir antes de aprovar


class PedidoDeGeracao(BaseModel):
    tipo: str = Field(max_length=12)
    quantidade: int = Field(default=3, ge=1, le=5)


@rotas.get("/entrar")
async def conferir():
    return {"ok": True}


@rotas.get("/conteudos")
async def listar(status: Optional[str] = None, c: Container = Depends(container)):
    return [conteudo(x) for x in reversed(await c.conteudos.lista(status))]


@rotas.post("/conteudos")
async def criar(pedido: PedidoDeConteudo, c: Container = Depends(container)):
    try:
        return conteudo(await c.conteudos.criar(pedido.tipo, pedido.dados))
    except ConteudoInvalido as erro:
        raise HTTPException(422, str(erro))


@rotas.post("/conteudos/{conteudo_id}/aprovar")
async def aprovar(conteudo_id: int, pedido: PedidoDeAprovacao, c: Container = Depends(container)):
    try:
        return conteudo(await c.conteudos.aprovar(conteudo_id, pedido.dados))
    except LookupError:
        raise HTTPException(404)
    except ConteudoInvalido as erro:
        raise HTTPException(422, str(erro))


@rotas.post("/conteudos/{conteudo_id}/recusar")
async def recusar(conteudo_id: int, c: Container = Depends(container)):
    try:
        return conteudo(await c.conteudos.recusar(conteudo_id))
    except LookupError:
        raise HTTPException(404)


@rotas.post("/gerar")
async def gerar(pedido: PedidoDeGeracao, c: Container = Depends(container)):
    try:
        return [conteudo(x) for x in await c.conteudos.gerar(pedido.tipo, pedido.quantidade)]
    except ConteudoInvalido as erro:
        raise HTTPException(422, str(erro))


@rotas.get("/denuncias")
async def denuncias(c: Container = Depends(container)):
    lista = await c.repositorio.denuncias()
    perfis = await c.repositorio.perfis({d["sobre_id"] for d in lista} | {d["de_id"] for d in lista})
    def quem(i):
        p = perfis.get(i)
        return {"id": i, "nome": p.nome if p else "?", "igreja": p.igreja_nome if p else "", "codinome": p.codinome if p else ""}
    return [{**d, "de": quem(d["de_id"]), "sobre": quem(d["sobre_id"])} for d in lista]
