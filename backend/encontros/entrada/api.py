"""API do app (FastAPI). Tudo, menos /entrar, /hobbies e /saude, exige o token no cabeçalho Authorization."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from encontros.aplicacao.conversas import NaoEncontrado, Recusado
from encontros.aplicacao.curadoria import Sugestao
from encontros.aplicacao.entrar import MUITAS_TENTATIVAS
from encontros.aplicacao.perfil import PerfilRecusado
from encontros.aplicacao.portas import Match, Mensagem
from encontros.config import Configuracao, configuracao
from encontros.container import Container, montar
from encontros.dominio.afinidade import Afinidade, distancia_entre, em_comum
from encontros.dominio.perfil import HOBBIES, HOBBIES_MINIMOS, Perfil, distancia_aproximada
from encontros.infraestrutura.fotos import FotoRecusada

logger = logging.getLogger(__name__)


# ---------------- formatos de entrada ----------------

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


class PedidoDeLocal(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    cidade: Optional[str] = Field(default=None, max_length=120)


class PedidoDeReacao(BaseModel):
    para_id: int
    curtiu: bool


class PedidoDeMensagem(BaseModel):
    texto: str = Field(max_length=4000)


class PedidoDeLeitura(BaseModel):
    ate: int = Field(ge=0)


class PedidoDeDenuncia(BaseModel):
    pessoa_id: int
    motivo: str = Field(default="", max_length=1000)


# ---------------- formatos de saída ----------------

def meu_perfil(p: Perfil) -> dict:
    return {"id": p.id, "nome": p.nome, "nome_publico": p.nome_publico, "idade": p.idade, "genero": p.genero.value,
            "cidade": p.cidade, "bairro": p.bairro, "igreja": p.igreja_nome, "hobbies": list(p.hobbies),
            "bio": p.bio, "tem_foto": p.tem_foto, "idade_min": p.idade_min, "idade_max": p.idade_max,
            "raio_km": p.raio_km, "visivel": p.visivel, "completo": p.completo,
            "tem_localizacao": p.coordenadas is not None, "local_do_app": bool(p.extras.get("local_do_app"))}


def cartao(p: Perfil, eu: Perfil, afinidade: Optional[Afinidade] = None) -> dict:
    """Como a pessoa aparece para os outros: primeiro nome, distância arredondada e nada de foto."""
    return {"id": p.id, "nome": p.nome_publico, "idade": p.idade, "cidade": p.cidade, "igreja": p.igreja_nome,
            "distancia_km": distancia_aproximada(distancia_entre(eu, p)), "hobbies": list(p.hobbies),
            "em_comum": list(afinidade.em_comum if afinidade else em_comum(eu, p)), "bio": p.bio,
            "afinidade": {"nivel": afinidade.nivel.value, "proximidade": afinidade.proximidade.value,
                          "origem": afinidade.origem} if afinidade else None}


def mensagem(m: Mensagem, eu_id: int) -> dict:
    return {"id": m.id, "texto": m.texto, "minha": m.autor_id == eu_id, "criado_em": m.criado_em}


def criar_app(montador: Callable[[Configuracao], Awaitable[Container]] = montar,
              config: Optional[Configuracao] = None) -> FastAPI:
    config = config or configuracao()

    @asynccontextmanager
    async def ciclo(app: FastAPI):
        app.state.c = await montador(config)
        yield
        await app.state.c.fechar()

    app = FastAPI(title="Basiléia Encontros", version="0.1.0", lifespan=ciclo)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in config.origens.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])

    def c(request: Request) -> Container:
        return request.app.state.c

    async def eu(request: Request, c: Container = Depends(c)) -> Perfil:
        cabecalho = request.headers.get("authorization", "")
        pessoa_id = c.tokens.pessoa_do_acesso(cabecalho[7:]) if cabecalho.lower().startswith("bearer ") else None
        pessoa = await c.repositorio.perfil(pessoa_id) if pessoa_id else None
        if not pessoa or not pessoa.elegivel:
            raise HTTPException(401, "Entre de novo.")
        return pessoa

    async def match_ou_404(c: Container, pessoa: Perfil, match_id: int, ativo: bool = True) -> Match:
        try:
            return await c.conversas.match_de(pessoa.id, match_id, ativo)
        except NaoEncontrado:
            raise HTTPException(404, "Conversa não encontrada.")

    # ---------------- entrada ----------------

    @app.get("/saude")
    async def saude():
        return {"ok": True, "demo": config.modo_demo}

    @app.get("/hobbies")
    async def hobbies():
        return {"hobbies": list(HOBBIES), "minimo": HOBBIES_MINIMOS}

    @app.get("/demo/contas")
    async def contas_demo():
        if not config.modo_demo:
            raise HTTPException(404)
        from encontros.infraestrutura.diretorio_demo import contas_de_teste
        return contas_de_teste()

    @app.post("/entrar")
    async def entrar(pedido: PedidoDeEntrada, request: Request, c: Container = Depends(c)):
        origem = request.client.host if request.client else "?"
        resultado = await c.entrar.executar(pedido.usuario, pedido.senha, origem, pedido.igreja_id)
        if resultado.erro:
            raise HTTPException(429 if resultado.erro == MUITAS_TENTATIVAS else 403, resultado.erro)
        if resultado.escolher:
            return {"escolher": [{"igreja_id": e.igreja_id, "igreja_nome": e.igreja_nome} for e in resultado.escolher]}
        return {"token": c.tokens.de_acesso(resultado.perfil.id), "perfil": meu_perfil(resultado.perfil)}

    # ---------------- o próprio perfil ----------------

    @app.get("/eu")
    async def ver_eu(pessoa: Perfil = Depends(eu)):
        return meu_perfil(pessoa)

    @app.put("/eu")
    async def mudar_eu(pedido: PedidoDePerfil, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        try:
            novo = await c.atualizar_perfil.executar(pessoa, **pedido.model_dump(exclude_none=True))
        except PerfilRecusado as erro:
            raise HTTPException(422, str(erro))
        return meu_perfil(novo)

    @app.post("/eu/localizacao")
    async def mudar_local(pedido: PedidoDeLocal, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        # guardada arredondada (~1 km): o suficiente para a distância, sem apontar a casa
        novo = await c.repositorio.definir_local(pessoa.id, round(pedido.lat, 2), round(pedido.lon, 2),
                                                 (pedido.cidade or "").strip() or None)
        return meu_perfil(novo)

    @app.post("/eu/foto")
    async def mandar_foto(foto: UploadFile = File(...), pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        try:
            nome = c.fotos.salvar(await foto.read())
        except FotoRecusada as erro:
            raise HTTPException(422, str(erro))
        antiga = pessoa.extras.get("foto")
        novo = await c.repositorio.atualizar_perfil(pessoa.id, foto=nome)
        c.fotos.apagar(antiga)
        return meu_perfil(novo)

    @app.get("/fotos/{pessoa_id}")
    async def ver_foto(pessoa_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        """A foto só sai para a própria pessoa ou para quem tem match com ela E recebeu a liberação."""
        if not await c.conversas.pode_ver_foto(pessoa.id, pessoa_id):
            raise HTTPException(404)
        dono = await c.repositorio.perfil(pessoa_id)
        caminho = c.fotos.caminho(dono.extras.get("foto") if dono else None)
        if not caminho:
            raise HTTPException(404)
        return FileResponse(caminho, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})

    # ---------------- descobrir ----------------

    @app.get("/descobrir")
    async def descobrir(pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        if not pessoa.completo:
            return {"pronto": False, "cartoes": []}
        sugestoes: List[Sugestao] = await c.curadoria.feed(pessoa)
        return {"pronto": True, "cartoes": [cartao(s.pessoa, pessoa, s.afinidade) for s in sugestoes]}

    @app.post("/reacoes")
    async def reagir(pedido: PedidoDeReacao, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        try:
            match = await c.conversas.reagir(pessoa, pedido.para_id, pedido.curtiu)
        except NaoEncontrado:
            raise HTTPException(404, "Pessoa não encontrada.")
        except Recusado as erro:
            raise HTTPException(409, str(erro))
        if not match:
            return {"match": None}
        outra = await c.repositorio.perfil(match.outra(pessoa.id))
        return {"match": {"id": match.id, "pessoa": cartao(outra, pessoa)}}

    # ---------------- matches e conversa ----------------

    @app.get("/matches")
    async def matches(pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        lista = await c.repositorio.matches_de(pessoa.id)
        outras = await c.repositorio.perfis([m.outra(pessoa.id) for m in lista])
        ultimas = await c.repositorio.ultimas_mensagens([m.id for m in lista])
        nao_lidas = await c.repositorio.nao_lidas(pessoa.id, {m.id: m.lido_ate.get(pessoa.id, 0) for m in lista})
        saida = []
        for m in lista:
            outra = outras.get(m.outra(pessoa.id))
            if not outra or not outra.elegivel:
                continue
            ultima = ultimas.get(m.id)
            saida.append({"id": m.id, "criado_em": m.criado_em, "pessoa": cartao(outra, pessoa),
                          "foto_liberada": bool(m.foto_liberada.get(outra.id)),
                          "eu_liberei": bool(m.foto_liberada.get(pessoa.id)),
                          "ultima": mensagem(ultima, pessoa.id) if ultima else None,
                          "nao_lidas": nao_lidas.get(m.id, 0)})
        saida.sort(key=lambda x: (x["ultima"] or {}).get("criado_em") or x["criado_em"], reverse=True)
        return saida

    @app.get("/matches/{match_id}")
    async def um_match(match_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        m = await match_ou_404(c, pessoa, match_id)
        outra = await c.repositorio.perfil(m.outra(pessoa.id))
        return {"id": m.id, "criado_em": m.criado_em, "pessoa": cartao(outra, pessoa),
                "foto_liberada": bool(m.foto_liberada.get(outra.id)), "eu_liberei": bool(m.foto_liberada.get(pessoa.id))}

    @app.get("/matches/{match_id}/mensagens")
    async def ler_mensagens(match_id: int, depois_de: int = 0, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        m = await match_ou_404(c, pessoa, match_id)
        lista = await c.conversas.mensagens(pessoa.id, match_id, depois_de)
        return {"mensagens": [mensagem(x, pessoa.id) for x in lista],
                "foto_liberada": bool(m.foto_liberada.get(m.outra(pessoa.id))),
                "eu_liberei": bool(m.foto_liberada.get(pessoa.id))}

    @app.post("/matches/{match_id}/mensagens")
    async def mandar_mensagem(match_id: int, pedido: PedidoDeMensagem, pessoa: Perfil = Depends(eu),
                              c: Container = Depends(c)):
        await match_ou_404(c, pessoa, match_id)
        try:
            return mensagem(await c.conversas.enviar(pessoa.id, match_id, pedido.texto), pessoa.id)
        except Recusado as erro:
            raise HTTPException(422, str(erro))

    @app.post("/matches/{match_id}/lido")
    async def marcar_lido(match_id: int, pedido: PedidoDeLeitura, pessoa: Perfil = Depends(eu),
                          c: Container = Depends(c)):
        await match_ou_404(c, pessoa, match_id)
        await c.repositorio.marcar_lido(match_id, pessoa.id, pedido.ate)
        return {"ok": True}

    @app.post("/matches/{match_id}/liberar-foto")
    async def liberar_foto(match_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        await match_ou_404(c, pessoa, match_id)
        await c.conversas.liberar_foto(pessoa.id, match_id)
        return {"ok": True}

    @app.delete("/matches/{match_id}")
    async def desfazer(match_id: int, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        await match_ou_404(c, pessoa, match_id)
        await c.repositorio.desfazer(match_id, pessoa.id)
        return {"ok": True}

    @app.post("/denuncias")
    async def denunciar(pedido: PedidoDeDenuncia, pessoa: Perfil = Depends(eu), c: Container = Depends(c)):
        """Denunciar também desfaz o match (se houver) e esconde as duas pessoas uma da outra."""
        if pedido.pessoa_id == pessoa.id or not await c.repositorio.perfil(pedido.pessoa_id):
            raise HTTPException(404)
        await c.repositorio.denunciar(pessoa.id, pedido.pessoa_id, pedido.motivo)
        match = await c.repositorio.match_entre(pessoa.id, pedido.pessoa_id)
        if match:
            await c.repositorio.desfazer(match.id, pessoa.id)
        logger.warning("[encontros] denúncia: pessoa %s sobre %s", pessoa.id, pedido.pessoa_id)
        return {"ok": True}

    return app
