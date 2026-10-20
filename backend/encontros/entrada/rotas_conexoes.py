"""Sinais do dia, conexões, revelações, pergunta a dois, chat e denúncia."""
from __future__ import annotations

import functools

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from encontros.aplicacao.jornada import NaoEncontrado, Recusado
from encontros.container import Container
from encontros.dominio.perfil import Perfil
from encontros.entrada.dependencias import container, eu
from encontros.entrada.formatos import (evento, mensagem, minhas_revelacoes, pergunta, publico, resumo_da_conexao,
                                        sinal)

rotas = APIRouter()


class PedidoDeSinal(BaseModel):
    para_id: int
    enviar: bool


class PedidoDeItem(BaseModel):
    item: str = Field(max_length=20)


class PedidoDeTexto(BaseModel):
    texto: str = Field(max_length=4000)


class PedidoDeLeitura(BaseModel):
    ate: int = Field(ge=0)


class PedidoDeDenuncia(BaseModel):
    pessoa_id: int
    motivo: str = Field(default="", max_length=1000)


def _erros(funcao):
    """NaoEncontrado → 404 e Recusado → 422, sem repetir try/except em toda rota."""
    @functools.wraps(funcao)
    async def envolvida(*args, **kwargs):
        try:
            return await funcao(*args, **kwargs)
        except NaoEncontrado:
            raise HTTPException(404, "Não encontrado.")
        except Recusado as erro:
            raise HTTPException(422, str(erro))
    return envolvida


# ---------------- sinais do dia ----------------

@rotas.get("/sinais")
@_erros
async def sinais(pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    if not pessoa.completo:
        return {"pronto": False, "sinais": [], "demo": c.config.modo_demo}
    lista = await c.conexoes.sinais(pessoa)
    return {"pronto": True, "sinais": [sinal(s, pessoa) for s in lista], "demo": c.config.modo_demo}


@rotas.post("/sinais")
@_erros
async def responder_sinal(pedido: PedidoDeSinal, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    conexao = await c.conexoes.responder_sinal(pessoa, pedido.para_id, pedido.enviar)
    if not conexao:
        return {"conexao": None}
    conexao, outra = await c.conexoes.conexao_de(pessoa, conexao.id)
    visao = c.conexoes.visao(conexao, pessoa, outra)
    return {"conexao": {"id": conexao.id, "pontos": conexao.pontos, "outra": publico(outra, pessoa, visao.dela)}}


@rotas.post("/sinais/mais")
@_erros
async def mais_sinais(pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    await c.conexoes.mais_sinais(pessoa)
    return {"ok": True}


# ---------------- conexões ----------------

@rotas.get("/conexoes")
async def conexoes(pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    lista = await c.repositorio.conexoes_de(pessoa.id)
    outras = await c.repositorio.perfis([x.outra(pessoa.id) for x in lista])
    ultimas = await c.repositorio.ultimas_mensagens([x.id for x in lista])
    nao_lidas = await c.repositorio.nao_lidas(pessoa.id, {x.id: x.lido_ate.get(pessoa.id, 0) for x in lista})
    saida = []
    for x in lista:
        outra = outras.get(x.outra(pessoa.id))
        if not outra or not outra.elegivel:
            continue
        visao = c.conexoes.visao(x, pessoa, outra)
        vez = await c.conexoes.pergunta_da_vez(x, pessoa)
        ultima = ultimas.get(x.id) if visao.chat_aberto else None
        saida.append(resumo_da_conexao(visao, pessoa, {
            "ultima": mensagem(ultima, pessoa.id) if ultima else None,
            "nao_lidas": nao_lidas.get(x.id, 0) if visao.chat_aberto else 0,
            "pergunta_pendente": bool(vez.conteudo and not vez.minha)}))
    saida.sort(key=lambda r: (-(r["nao_lidas"] > 0), -r["pergunta_pendente"], -r["pontos"]))
    return saida


@rotas.get("/conexoes/{conexao_id}")
@_erros
async def uma_conexao(conexao_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    conexao, outra = await c.conexoes.conexao_de(pessoa, conexao_id)
    visao = c.conexoes.visao(conexao, pessoa, outra)
    vez = await c.conexoes.pergunta_da_vez(conexao, pessoa)
    return resumo_da_conexao(visao, pessoa, {
        "minhas": minhas_revelacoes(visao), "pergunta": pergunta(vez),
        "eventos": [evento(e) for e in await c.repositorio.eventos(conexao.id, 15)]})


@rotas.post("/conexoes/{conexao_id}/liberar")
@_erros
async def liberar(conexao_id: int, pedido: PedidoDeItem, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    await c.conexoes.liberar(pessoa, conexao_id, pedido.item)
    return {"ok": True}


@rotas.post("/conexoes/{conexao_id}/pergunta")
@_erros
async def responder_pergunta(conexao_id: int, pedido: PedidoDeTexto, pessoa: Perfil = Depends(eu),
                             c: Container = Depends(container)):
    feito = await c.conexoes.responder_pergunta(pessoa, conexao_id, pedido.texto)
    return {"evento": evento(feito) if feito else None}


@rotas.get("/conexoes/{conexao_id}/mensagens")
@_erros
async def ler_mensagens(conexao_id: int, depois_de: int = 0, pessoa: Perfil = Depends(eu),
                        c: Container = Depends(container)):
    lista = await c.conexoes.mensagens(pessoa, conexao_id, depois_de)
    return {"mensagens": [mensagem(m, pessoa.id) for m in lista]}


@rotas.post("/conexoes/{conexao_id}/mensagens")
@_erros
async def mandar_mensagem(conexao_id: int, pedido: PedidoDeTexto, pessoa: Perfil = Depends(eu),
                          c: Container = Depends(container)):
    return mensagem(await c.conexoes.enviar(pessoa, conexao_id, pedido.texto), pessoa.id)


@rotas.post("/conexoes/{conexao_id}/lido")
@_erros
async def marcar_lido(conexao_id: int, pedido: PedidoDeLeitura, pessoa: Perfil = Depends(eu),
                      c: Container = Depends(container)):
    await c.conexoes.conexao_de(pessoa, conexao_id)
    await c.repositorio.marcar_lido(conexao_id, pessoa.id, pedido.ate)
    return {"ok": True}


@rotas.delete("/conexoes/{conexao_id}")
@_erros
async def desfazer(conexao_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    await c.conexoes.conexao_de(pessoa, conexao_id)
    await c.repositorio.desfazer(conexao_id, pessoa.id)
    return {"ok": True}


@rotas.post("/denuncias")
async def denunciar(pedido: PedidoDeDenuncia, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    """Denunciar também encerra a conexão (se houver) e esconde as duas pessoas uma da outra."""
    if pedido.pessoa_id == pessoa.id or not await c.repositorio.perfil(pedido.pessoa_id):
        raise HTTPException(404)
    await c.repositorio.denunciar(pessoa.id, pedido.pessoa_id, pedido.motivo)
    conexao = await c.repositorio.conexao_entre(pessoa.id, pedido.pessoa_id)
    if conexao:
        await c.repositorio.desfazer(conexao.id, pessoa.id)
    return {"ok": True}
