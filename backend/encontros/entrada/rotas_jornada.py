"""A jornada pessoal: resumo, devocional do dia e testes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from encontros.container import Container
from encontros.dominio.perfil import Perfil
from encontros.entrada.dependencias import container, eu
from encontros.entrada.formatos import devocional, jornada, teste
from encontros.entrada.rotas_conexoes import PedidoDeTexto, _erros

rotas = APIRouter(prefix="/jornada")


class PedidoDeTeste(BaseModel):
    escolhas: List[int] = Field(max_length=20)


@rotas.get("")
async def ver_jornada(pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    do_dia = await c.jornada.devocional_de_hoje()
    minha = (await c.repositorio.resposta(pessoa.id, do_dia.id)) if do_dia else None
    return {**jornada(await c.jornada.resumo(pessoa)),
            "devocional": devocional(do_dia, minha.dados.get("texto") if minha else None) if do_dia else None,
            "testes": [teste(t, feito) for t, feito in await c.jornada.testes(pessoa)]}


@rotas.post("/devocional")
@_erros
async def fazer_devocional(pedido: PedidoDeTexto, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    ganho = await c.jornada.responder_devocional(pessoa, pedido.texto)
    return {"ganhou": ganho, **jornada(await c.jornada.resumo(await c.repositorio.perfil(pessoa.id)))}


@rotas.get("/testes/{teste_id}")
@_erros
async def ver_teste(teste_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    t = await c.jornada.teste(teste_id)
    return teste(t, bool(await c.repositorio.resposta(pessoa.id, t.id)), com_questoes=True)


@rotas.post("/testes/{teste_id}")
@_erros
async def fazer_teste(teste_id: int, pedido: PedidoDeTeste, pessoa: Perfil = Depends(eu),
                      c: Container = Depends(container)):
    ganho = await c.jornada.responder_teste(pessoa, teste_id, pedido.escolhas)
    return {"ganhou": ganho, **jornada(await c.jornada.resumo(await c.repositorio.perfil(pessoa.id)))}
