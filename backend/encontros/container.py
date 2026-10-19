"""Monta as peças a partir da configuração (CRM de verdade ou de demonstração, JEV ou só regras)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from encontros.aplicacao.conversas import Conversas
from encontros.aplicacao.curadoria import Curadoria
from encontros.aplicacao.entrar import Entrar, Liberacao
from encontros.aplicacao.perfil import AtualizarPerfil
from encontros.config import Configuracao
from encontros.infraestrutura.banco import criar_motor, criar_sessoes, criar_tabelas
from encontros.infraestrutura.fotos import Fotos
from encontros.infraestrutura.julgador import ClienteOpenRouter, JulgadorComReserva, JulgadorJev, JulgadorLLM
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
    conversas: Conversas
    _fechar: tuple = ()

    async def fechar(self) -> None:
        for fechar in self._fechar:
            await fechar()


def _julgador(config: Configuracao, fechar: list) -> Optional[JulgadorComReserva]:
    if not config.openrouter_api_key:
        logger.warning("[encontros] sem ENCONTROS_OPENROUTER_API_KEY: afinidade só pelas regras (hobbies iguais)")
        return None
    cliente = ClienteOpenRouter(config.openrouter_api_key)
    fechar.append(cliente.fechar)
    provedores = [config.provedor_reserva] if config.provedor_reserva else None
    return JulgadorComReserva(JulgadorJev(cliente, config.modelo_jev),
                              JulgadorLLM(cliente, config.modelo_reserva, provedores))


async def montar(config: Configuracao) -> Container:
    if config.database_url.startswith("sqlite"):
        Path(config.database_url.split("///", 1)[-1]).parent.mkdir(parents=True, exist_ok=True)
    motor = criar_motor(config.database_url)
    await criar_tabelas(motor)
    repositorio = RepositorioSql(criar_sessoes(motor))
    fotos = Fotos(config.pasta_fotos)
    fechar = [motor.dispose]

    if config.modo_demo:
        from encontros.infraestrutura.diretorio_demo import DiretorioDemo, semear
        logger.warning("[encontros] MODO DEMONSTRAÇÃO: CRM de mentira, não usar em produção")
        diretorio, liberacao = DiretorioDemo(), Liberacao.de_texto("*")
        await semear(repositorio, fotos)
    else:
        from encontros.infraestrutura.crm_mongo import DiretorioMongo
        if not config.mongo_uri:
            raise RuntimeError("ENCONTROS_MONGO_URI é obrigatório (ou ENCONTROS_MODO_DEMO=true para testar)")
        diretorio, liberacao = DiretorioMongo(config.mongo_uri, config.mongo_db), Liberacao.de_texto(config.igrejas)
        fechar.append(diretorio.fechar)

    julgador = _julgador(config, fechar)
    curadoria = Curadoria(repositorio, julgador, julgar_por_vez=config.julgar_por_vez)
    segredo = config.jwt_secret or ("demo-" * 4 if config.modo_demo else "")
    return Container(
        config=config, repositorio=repositorio, fotos=fotos, tokens=TokensJwt(segredo, config.dias_de_acesso),
        entrar=Entrar(diretorio, repositorio, liberacao, config.estados_civis_permitidos, config.idade_minima),
        atualizar_perfil=AtualizarPerfil(repositorio, julgador), curadoria=curadoria,
        conversas=Conversas(repositorio, curadoria), _fechar=tuple(reversed(fechar)))
