"""Monta as peças a partir da configuração (CRM de verdade e/ou de teste, JEV ou só regras)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from encontros.aplicacao.comparador import Comparador
from encontros.aplicacao.conexoes import Conexoes
from encontros.aplicacao.conteudo import Conteudos
from encontros.aplicacao.curadoria import Curadoria
from encontros.aplicacao.entrar import Entrar, Liberacao
from encontros.aplicacao.jornada import Jornada
from encontros.aplicacao.perfil import AtualizarPerfil
from encontros.aplicacao.pontuacao import Pontuacao
from encontros.config import Configuracao
from encontros.infraestrutura.banco import criar_motor, criar_sessoes, criar_tabelas
from encontros.infraestrutura.fotos import Fotos
from encontros.infraestrutura.julgador import (ClienteOpenRouter, EscritorLLM, JulgadorComReserva, JulgadorJev,
                                               JulgadorLLM)
from encontros.infraestrutura.repositorio_sql import RepositorioSql
from encontros.infraestrutura.tokens import TokensJwt

logger = logging.getLogger(__name__)


@dataclass
class Container:
    config: Configuracao
    repositorio: RepositorioSql
    fotos: Fotos
    tokens: TokensJwt
    entrar: Entrar
    atualizar_perfil: AtualizarPerfil
    curadoria: Curadoria
    conexoes: Conexoes
    jornada: Jornada
    conteudos: Conteudos
    bots: Optional[object] = None
    chave_lider: str = ""
    _fechar: tuple = ()

    async def fechar(self) -> None:
        for fechar in self._fechar:
            await fechar()


async def montar(config: Configuracao) -> Container:
    if config.database_url.startswith("sqlite"):
        Path(config.database_url.split("///", 1)[-1]).parent.mkdir(parents=True, exist_ok=True)
    motor = criar_motor(config.database_url)
    await criar_tabelas(motor)
    repositorio = RepositorioSql(criar_sessoes(motor))
    fotos = Fotos(config.pasta_fotos)
    fechar = [motor.dispose]

    julgador, escritor = None, None
    if config.openrouter_api_key:
        cliente = ClienteOpenRouter(config.openrouter_api_key)
        fechar.append(cliente.fechar)
        provedores = [config.provedor_reserva] if config.provedor_reserva else None
        julgador = JulgadorComReserva(JulgadorJev(cliente, config.modelo_jev),
                                      JulgadorLLM(cliente, config.modelo_reserva, provedores))
        escritor = EscritorLLM(cliente, config.modelo_escritor, provedores)
    else:
        logger.warning("[encontros] sem ENCONTROS_OPENROUTER_API_KEY: afinidade só pelas regras, sem gerar conteúdo")

    real = None
    if config.mongo_uri:
        from encontros.infraestrutura.crm_mongo import DiretorioMongo
        real = DiretorioMongo(config.mongo_uri, config.mongo_db)
        fechar.append(real.fechar)
    elif not config.modo_demo:
        raise RuntimeError("ENCONTROS_MONGO_URI é obrigatório (ou ENCONTROS_MODO_DEMO=true para testar)")

    bots = None
    if config.modo_demo:
        from encontros.infraestrutura.diretorio_demo import (BotsDeTeste, DiretorioCombinado, DiretorioDemo,
                                                             semear_conteudo, semear_pessoas)
        logger.warning("[encontros] MODO DE TESTE ligado: contas e perfis de teste, não usar com o público")
        diretorio = DiretorioCombinado(DiretorioDemo(), real) if real else DiretorioDemo()
        liberacao = Liberacao.de_texto(f"{config.igrejas},demo-igreja" if real else "*")
        await semear_conteudo(repositorio, aprovado=True)
        bots = BotsDeTeste(repositorio, await semear_pessoas(repositorio, fotos))
        await bots.responder_testes()
    else:
        from encontros.infraestrutura.diretorio_demo import semear_conteudo
        diretorio, liberacao = real, Liberacao.de_texto(config.igrejas)
        await semear_conteudo(repositorio, aprovado=False)     # em produção, o líder aprova antes

    curadoria = Curadoria(repositorio, julgador, julgar_por_vez=config.julgar_por_vez)
    comparador = Comparador(julgador)
    pontuacao = Pontuacao(repositorio, comparador)
    conexoes = Conexoes(repositorio, curadoria, pontuacao, bots, demo=config.modo_demo)
    if bots:
        bots.conexoes = conexoes
    segredo = config.jwt_secret or ("demo-" * 4 if config.modo_demo else "")
    chave_lider = config.chave_lider or ("lider-teste" if config.modo_demo else "")
    return Container(
        config=config, repositorio=repositorio, fotos=fotos, tokens=TokensJwt(segredo, config.dias_de_acesso),
        entrar=Entrar(diretorio, repositorio, liberacao, config.estados_civis_permitidos, config.idade_minima),
        atualizar_perfil=AtualizarPerfil(repositorio, julgador), curadoria=curadoria, conexoes=conexoes,
        jornada=Jornada(repositorio, comparador, pontuacao, bots), conteudos=Conteudos(repositorio, escritor),
        bots=bots, chave_lider=chave_lider, _fechar=tuple(reversed(fechar)))
