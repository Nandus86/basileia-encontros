"""Entrar, o próprio perfil (hobbies, foto, preferências, o que revelar e quando) e as fotos."""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from encontros.aplicacao.entrar import MUITAS_TENTATIVAS
from encontros.aplicacao.perfil import PerfilRecusado
from encontros.container import Container
from encontros.dominio.jornada import LIMIARES_POSSIVEIS, ROTULOS
from encontros.dominio.perfil import HOBBIES, HOBBIES_MINIMOS, Perfil
from encontros.entrada.dependencias import container, eu
from encontros.entrada.formatos import meu_perfil
from encontros.infraestrutura.fotos import FotoRecusada

rotas = APIRouter()


class PedidoDeEntrada(BaseModel):
    usuario: str = Field(max_length=40)
    senha: str = Field(max_length=40)
    igreja_id: Optional[str] = Field(default=None, max_length=40)


class PedidoDePerfil(BaseModel):
    hobbies: Optional[List[str]] = Field(default=None, max_length=40)
    bio: Optional[str] = Field(default=None, max_length=2000)
    idade_min: Optional[int] = Field(default=None, ge=18, le=99)
    idade_max: Optional[int] = Field(default=None, ge=18, le=99)
    raio_km: Optional[int] = Field(default=None, ge=1, le=200)
    visivel: Optional[bool] = None


class PedidoDeRevelacoes(BaseModel):
    limites: Dict[str, Optional[int]]


class PedidoDeLocal(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    cidade: Optional[str] = Field(default=None, max_length=120)


@rotas.get("/saude")
async def saude(c: Container = Depends(container)):
    return {"ok": True, "demo": c.config.modo_demo}


@rotas.get("/hobbies")
async def hobbies():
    return {"hobbies": list(HOBBIES), "minimo": HOBBIES_MINIMOS}


@rotas.get("/demo/contas")
async def contas_demo(c: Container = Depends(container)):
    if not c.config.modo_demo:
        raise HTTPException(404)
    from encontros.infraestrutura.diretorio_demo import contas_de_teste
    return contas_de_teste()


@rotas.post("/entrar")
async def entrar(pedido: PedidoDeEntrada, request: Request, c: Container = Depends(container)):
    origem = request.client.host if request.client else "?"
    resultado = await c.entrar.executar(pedido.usuario, pedido.senha, origem, pedido.igreja_id)
    if resultado.erro:
        raise HTTPException(429 if resultado.erro == MUITAS_TENTATIVAS else 403, resultado.erro)
    if resultado.escolher:
        return {"escolher": [{"igreja_id": e.igreja_id, "igreja_nome": e.igreja_nome} for e in resultado.escolher]}
    if c.bots:
        await c.bots.ao_entrar(resultado.perfil)
    return {"token": c.tokens.de_acesso(resultado.perfil.id), "perfil": meu_perfil(resultado.perfil)}


@rotas.get("/eu")
async def ver_eu(pessoa: Perfil = Depends(eu)):
    return meu_perfil(pessoa)


@rotas.put("/eu")
async def mudar_eu(pedido: PedidoDePerfil, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    try:
        novo = await c.atualizar_perfil.executar(pessoa, **pedido.model_dump(exclude_none=True))
    except PerfilRecusado as erro:
        raise HTTPException(422, str(erro))
    return meu_perfil(novo)


@rotas.put("/eu/revelacoes")
async def mudar_revelacoes(pedido: PedidoDeRevelacoes, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    """Com quantos pontos de afinidade cada coisa é revelada (null = só quando eu liberar na mão)."""
    novos = dict(pessoa.revelacoes)
    for item, limite in pedido.limites.items():
        if item not in ROTULOS or (limite is not None and limite not in LIMIARES_POSSIVEIS):
            raise HTTPException(422, "Limite inválido.")
        novos[item] = limite
    return meu_perfil(await c.repositorio.atualizar_perfil(pessoa.id, revelacoes=novos))


@rotas.post("/eu/localizacao")
async def mudar_local(pedido: PedidoDeLocal, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    # guardada arredondada (~1 km): o suficiente para a distância, sem apontar a casa
    novo = await c.repositorio.definir_local(pessoa.id, round(pedido.lat, 2), round(pedido.lon, 2),
                                             (pedido.cidade or "").strip() or None)
    return meu_perfil(novo)


@rotas.post("/eu/foto")
async def mandar_foto(foto: UploadFile = File(...), pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    try:
        nome = c.fotos.salvar(await foto.read())
    except FotoRecusada as erro:
        raise HTTPException(422, str(erro))
    antiga = pessoa.extras.get("foto")
    novo = await c.repositorio.atualizar_perfil(pessoa.id, foto=nome)
    c.fotos.apagar(antiga)
    return meu_perfil(novo)


@rotas.get("/fotos/{pessoa_id}")
async def ver_foto(pessoa_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(container)):
    """A foto só sai para a própria pessoa ou para a conexão em que ela revelou a foto."""
    if not await c.conexoes.pode_ver_foto(pessoa.id, pessoa_id):
        raise HTTPException(404)
    dono = await c.repositorio.perfil(pessoa_id)
    caminho = c.fotos.caminho(dono.extras.get("foto") if dono else None)
    if not caminho:
        raise HTTPException(404)
    return FileResponse(caminho, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})
