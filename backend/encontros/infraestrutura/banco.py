"""Tabelas do app (SQLAlchemy). Roda em Postgres (produção) ou SQLite (no computador / modo demonstração).

MVP: ao subir, as tabelas novas são criadas (create_all) e as colunas novas das tabelas que já existiam
são acrescentadas (sincronizar_colunas, só ADD COLUMN com valor padrão). Mudança maior → migrações de verdade.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
                        event, inspect, text)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PessoaTb(Base):
    __tablename__ = "encontros_pessoas"
    __table_args__ = (UniqueConstraint("igreja_id", "membro_id"),
                      Index("ix_encontros_pessoas_descobrir", "elegivel", "visivel", "genero", "idade"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    membro_id: Mapped[str] = mapped_column(String(40))
    igreja_id: Mapped[str] = mapped_column(String(40))
    igreja_nome: Mapped[str] = mapped_column(String(200), default="")
    nome: Mapped[str] = mapped_column(String(200), default="")
    genero: Mapped[str] = mapped_column(String(10))
    idade: Mapped[int] = mapped_column(Integer)
    cidade: Mapped[str] = mapped_column(String(120), default="")
    bairro: Mapped[str] = mapped_column(String(120), default="")
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    local_do_app: Mapped[bool] = mapped_column(Boolean, default=False)   # a pessoa usou a localização do celular
    hobbies: Mapped[list] = mapped_column(JSON, default=list)
    bio: Mapped[str] = mapped_column(Text, default="")
    foto: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    idade_min: Mapped[int] = mapped_column(Integer, default=18)
    idade_max: Mapped[int] = mapped_column(Integer, default=99)
    raio_km: Mapped[int] = mapped_column(Integer, default=30)
    visivel: Mapped[bool] = mapped_column(Boolean, default=True)
    elegivel: Mapped[bool] = mapped_column(Boolean, default=True)
    codinome: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    simbolo: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    jornada: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sequencia: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ultimo_devocional: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    revelacoes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)


class ReacaoTb(Base):
    __tablename__ = "encontros_reacoes"

    de_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True)
    para_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True,
                                         index=True)
    curtiu: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class MatchTb(Base):
    """A conexão (os dois enviaram sinal). foto_a/foto_b são da primeira versão; hoje vale `liberados_*`."""
    __tablename__ = "encontros_matches"
    __table_args__ = (UniqueConstraint("a_id", "b_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    a_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), index=True)
    b_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), index=True)
    foto_a: Mapped[bool] = mapped_column(Boolean, default=False)
    foto_b: Mapped[bool] = mapped_column(Boolean, default=False)
    lido_a: Mapped[int] = mapped_column(Integer, default=0)
    lido_b: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    desfeito_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    desfeito_por: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pontos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sintonia_soma: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    sintonia_qtd: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    liberados_a: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)     # itens que a liberou na mão
    liberados_b: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class MensagemTb(Base):
    __tablename__ = "encontros_mensagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("encontros_matches.id", ondelete="CASCADE"), index=True)
    autor_id: Mapped[int] = mapped_column(Integer)
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class AfinidadeTb(Base):
    """O julgamento de cada par (a_id < b_id), reaproveitado enquanto a assinatura dos dois perfis não mudar."""
    __tablename__ = "encontros_afinidades"

    a_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True)
    b_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True,
                                      index=True)
    assinatura: Mapped[str] = mapped_column(String(40))
    nivel: Mapped[str] = mapped_column(String(10))
    proximidade: Mapped[str] = mapped_column(String(10))
    apresentar: Mapped[bool] = mapped_column(Boolean)
    em_comum: Mapped[list] = mapped_column(JSON, default=list)
    origem: Mapped[str] = mapped_column(String(10))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)


class DenunciaTb(Base):
    __tablename__ = "encontros_denuncias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    de_id: Mapped[int] = mapped_column(Integer, index=True)
    sobre_id: Mapped[int] = mapped_column(Integer, index=True)
    motivo: Mapped[str] = mapped_column(Text, default="")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class ConteudoTb(Base):
    """Devocional, pergunta a dois ou teste. A IA gera como pendente; o líder aprova."""
    __tablename__ = "encontros_conteudos"
    __table_args__ = (Index("ix_encontros_conteudos_tipo", "tipo", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(12))            # devocional, pergunta, teste
    status: Mapped[str] = mapped_column(String(10))          # pendente, aprovado, recusado
    origem: Mapped[str] = mapped_column(String(10))          # ia, semente
    dados: Mapped[dict] = mapped_column(JSON)
    dia: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)   # devocional: o dia em que saiu
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    decidido_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RespostaTb(Base):
    __tablename__ = "encontros_respostas"

    pessoa_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True)
    conteudo_id: Mapped[int] = mapped_column(ForeignKey("encontros_conteudos.id", ondelete="CASCADE"),
                                             primary_key=True, index=True)
    dados: Mapped[dict] = mapped_column(JSON)               # {"texto": …} ou {"escolhas": [0..3, …]}
    temas: Mapped[list] = mapped_column(JSON, default=list)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class EventoDaDuplaTb(Base):
    """Cada ponto que a conexão ganhou e por quê. Um evento por conteúdo: ninguém pontua duas vezes."""
    __tablename__ = "encontros_eventos_dupla"
    __table_args__ = (UniqueConstraint("conexao_id", "referencia"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conexao_id: Mapped[int] = mapped_column(ForeignKey("encontros_matches.id", ondelete="CASCADE"), index=True)
    referencia: Mapped[str] = mapped_column(String(40))     # "inicio", "conteudo:12"
    tipo: Mapped[str] = mapped_column(String(12))
    titulo: Mapped[str] = mapped_column(String(200), default="")
    pontos: Mapped[int] = mapped_column(Integer)
    sintonia: Mapped[float] = mapped_column(Float)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class SugestaoTb(Base):
    """Os sinais do dia de cada pessoa: escolhidos uma vez por dia (poucos, de propósito)."""
    __tablename__ = "encontros_sugestoes"

    pessoa_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True)
    dia: Mapped[str] = mapped_column(String(10), primary_key=True)
    outro_id: Mapped[int] = mapped_column(ForeignKey("encontros_pessoas.id", ondelete="CASCADE"), primary_key=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    motivos: Mapped[list] = mapped_column(JSON, default=list)


def url_assincrona(url: str) -> str:
    """Aceita a URL como o Easypanel/Heroku entregam (postgres://…?sslmode=disable) e passa para o asyncpg,
    que quer postgresql+asyncpg:// e entende "ssl" no lugar de "sslmode"."""
    esquema, _, resto = url.partition("://")
    if esquema not in ("postgres", "postgresql"):
        return url
    endereco, _, consulta = resto.partition("?")
    parametros = [("ssl" if k == "sslmode" else k, v) for k, v in parse_qsl(consulta, keep_blank_values=True)]
    return f"postgresql+asyncpg://{endereco}" + (f"?{urlencode(parametros)}" if parametros else "")


def criar_motor(url: str) -> AsyncEngine:
    url = url_assincrona(url)
    if url.startswith("sqlite"):
        motor = create_async_engine(url, connect_args={"timeout": 15})

        @event.listens_for(motor.sync_engine, "connect")
        def _ajustar(conexao, _):
            # WAL: cada gravação deixa de esperar o disco inteiro (no Windows, de ~0,5 s para milissegundos)
            cursor = conexao.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        return motor
    return create_async_engine(url, pool_size=5, max_overflow=5, pool_pre_ping=True)


def criar_sessoes(motor: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(motor, expire_on_commit=False)


def sincronizar_colunas(conexao) -> list:
    """Acrescenta nas tabelas que já existiam as colunas novas do modelo (sempre com valor padrão ou nulas)."""
    existentes = inspect(conexao)
    novas = []
    for tabela in Base.metadata.sorted_tables:
        if not existentes.has_table(tabela.name):
            continue
        tem = {c["name"] for c in existentes.get_columns(tabela.name)}
        for coluna in tabela.columns:
            if coluna.name in tem:
                continue
            tipo = coluna.type.compile(dialect=conexao.dialect)
            padrao = f" DEFAULT {coluna.server_default.arg}" if coluna.server_default is not None else ""
            conexao.execute(text(f'ALTER TABLE {tabela.name} ADD COLUMN {coluna.name} {tipo}{padrao}'))
            novas.append(f"{tabela.name}.{coluna.name}")
    return novas


async def criar_tabelas(motor: AsyncEngine) -> None:
    async with motor.begin() as conexao:
        await conexao.run_sync(Base.metadata.create_all)
        await conexao.run_sync(sincronizar_colunas)
