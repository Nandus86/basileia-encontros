"""Configuração: só variáveis com prefixo ENCONTROS_."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND = Path(__file__).resolve().parents[1]

# backend/.env e, por cima dele, o .env.test da raiz (segredos locais, fora do git)
ARQUIVOS_ENV = (_BACKEND / ".env", _BACKEND.parent / ".env.test")


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENCONTROS_", env_file=ARQUIVOS_ENV, extra="ignore")

    # Banco próprio: Postgres em produção (pode ser o servidor do Basile; as tabelas começam com "encontros_")
    database_url: str = "sqlite+aiosqlite:///./dados/encontros.db"
    pasta_fotos: str = "./dados/fotos"

    # Modo demonstração: CRM de mentira e perfis prontos (sem Mongo). Nunca em produção.
    modo_demo: bool = False

    # Mongo do CRM — o mesmo usuário só de leitura do Motor de Cuidado
    mongo_uri: str = ""
    mongo_db: str = "dexos_basileia"

    jwt_secret: str = ""
    dias_de_acesso: int = 30

    # Igrejas liberadas: ids separados por vírgula, ou "*" para todas (vazio = nenhuma)
    igrejas: str = ""
    # De onde o app pode chamar (CORS), separados por vírgula
    origens: str = "http://localhost:3020"

    # Quem pode usar: estados civis do cadastro (casado, solteiro, divorciado, separado, uniao_estavel, viuvo)
    estados_civis: str = "solteiro"
    idade_minima: int = 18

    # IA: o JEV julga a afinidade e a bio; a reserva entra se o JEV falhar; sem chave, só as regras
    openrouter_api_key: str = Field(default="", validation_alias=AliasChoices(
        "ENCONTROS_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"))
    modelo_jev: str = "~typesafe/jev-latest"
    modelo_reserva: str = "deepseek/deepseek-v4.1-flash"
    provedor_reserva: str = "DeepSeek"
    julgar_por_vez: int = 12

    porta: int = 8000
    nivel_log: str = "INFO"

    @property
    def estados_civis_permitidos(self) -> frozenset:
        return frozenset(e.strip() for e in self.estados_civis.split(",") if e.strip())


@lru_cache
def configuracao() -> Configuracao:
    return Configuracao()
