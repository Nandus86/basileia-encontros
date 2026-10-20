"""Implementa a porta Repositorio com SQLAlchemy (Postgres ou SQLite)."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from encontros.aplicacao.portas import Conexao, Conteudo, EventoDaDupla, Mensagem, Resposta, SinalDoDia
from encontros.dominio.afinidade import Afinidade, Nivel, Proximidade, par
from encontros.dominio.jornada import FUSO, sortear_codinome
from encontros.dominio.perfil import DadosDoCrm, Genero, Perfil
from encontros.infraestrutura.banco import (AfinidadeTb, ConteudoTb, DenunciaTb, EventoDaDuplaTb, MatchTb, MensagemTb,
                                            PessoaTb, ReacaoTb, RespostaTb, SugestaoTb, agora)

CAMPOS_EDITAVEIS = {"hobbies", "bio", "idade_min", "idade_max", "raio_km", "visivel", "foto", "jornada", "sequencia",
                    "ultimo_devocional", "revelacoes", "codinome", "simbolo"}


def _perfil(t: PessoaTb) -> Perfil:
    return Perfil(id=t.id, membro_id=t.membro_id, igreja_id=t.igreja_id, igreja_nome=t.igreja_nome, nome=t.nome,
                  genero=Genero(t.genero), idade=t.idade, cidade=t.cidade, bairro=t.bairro,
                  coordenadas=(t.lat, t.lon) if t.lat is not None and t.lon is not None else None,
                  hobbies=tuple(t.hobbies or ()), bio=t.bio or "", tem_foto=bool(t.foto), idade_min=t.idade_min,
                  idade_max=t.idade_max, raio_km=t.raio_km, visivel=t.visivel, elegivel=t.elegivel,
                  codinome=t.codinome or "", simbolo=t.simbolo or "", jornada=t.jornada or 0,
                  sequencia=t.sequencia or 0, ultimo_devocional=t.ultimo_devocional,
                  revelacoes=dict(t.revelacoes or {}), extras={"foto": t.foto, "local_do_app": t.local_do_app})


def _conexao(t: MatchTb) -> Conexao:
    return Conexao(id=t.id, a_id=t.a_id, b_id=t.b_id, criado_em=t.criado_em.isoformat(), pontos=t.pontos or 0,
                   sintonia=(t.sintonia_soma / t.sintonia_qtd) if t.sintonia_qtd else None,
                   liberados={t.a_id: frozenset(t.liberados_a or ()), t.b_id: frozenset(t.liberados_b or ())},
                   lido_ate={t.a_id: t.lido_a, t.b_id: t.lido_b}, desfeita=t.desfeito_em is not None)


def _mensagem(t: MensagemTb) -> Mensagem:
    return Mensagem(id=t.id, match_id=t.match_id, autor_id=t.autor_id, texto=t.texto, criado_em=t.criado_em.isoformat())


def _conteudo(t: ConteudoTb) -> Conteudo:
    return Conteudo(id=t.id, tipo=t.tipo, status=t.status, origem=t.origem, dados=dict(t.dados or {}), dia=t.dia,
                    criado_em=t.criado_em.isoformat())


def _resposta(t: RespostaTb) -> Resposta:
    return Resposta(pessoa_id=t.pessoa_id, conteudo_id=t.conteudo_id, dados=dict(t.dados or {}),
                    temas=tuple(t.temas or ()), criado_em=t.criado_em.isoformat())


def _evento(t: EventoDaDuplaTb) -> EventoDaDupla:
    return EventoDaDupla(tipo=t.tipo, titulo=t.titulo, pontos=t.pontos, sintonia=t.sintonia,
                         criado_em=t.criado_em.isoformat())


def _inicio_do_dia(dia: str) -> datetime:
    return datetime.fromisoformat(dia).replace(tzinfo=FUSO)


class RepositorioSql:
    def __init__(self, sessoes: async_sessionmaker):
        self._sessoes = sessoes

    # ---------------- perfis ----------------

    async def salvar_do_crm(self, dados: DadosDoCrm) -> Perfil:
        async with self._sessoes() as s:
            t = (await s.execute(select(PessoaTb).where(PessoaTb.igreja_id == dados.igreja_id,
                                                        PessoaTb.membro_id == dados.membro_id))).scalar_one_or_none()
            if t is None:
                t = PessoaTb(membro_id=dados.membro_id, igreja_id=dados.igreja_id, hobbies=[])
                s.add(t)
            t.igreja_nome, t.nome, t.genero, t.idade = dados.igreja_nome, dados.nome, dados.genero.value, dados.idade
            t.elegivel = True
            if not t.codinome:
                t.codinome, t.simbolo = sortear_codinome()
            if not t.local_do_app:
                t.cidade, t.bairro = dados.cidade, dados.bairro
                t.lat, t.lon = dados.coordenadas if dados.coordenadas else (None, None)
            await s.commit()
            return _perfil(t)

    async def marcar_inelegivel(self, igreja_id: str, membro_id: str) -> None:
        async with self._sessoes() as s:
            await s.execute(update(PessoaTb).where(PessoaTb.igreja_id == igreja_id, PessoaTb.membro_id == membro_id)
                            .values(elegivel=False))
            await s.commit()

    async def perfil(self, pessoa_id: int) -> Optional[Perfil]:
        async with self._sessoes() as s:
            t = await s.get(PessoaTb, pessoa_id)
            return _perfil(t) if t else None

    async def perfis(self, ids: Sequence[int]) -> Dict[int, Perfil]:
        if not ids:
            return {}
        async with self._sessoes() as s:
            linhas = (await s.execute(select(PessoaTb).where(PessoaTb.id.in_(list(ids))))).scalars()
            return {t.id: _perfil(t) for t in linhas}

    async def atualizar_perfil(self, pessoa_id: int, **campos) -> Perfil:
        async with self._sessoes() as s:
            t = await s.get(PessoaTb, pessoa_id)
            for nome, valor in campos.items():
                if nome in CAMPOS_EDITAVEIS:
                    setattr(t, nome, list(valor) if nome == "hobbies" else dict(valor) if nome == "revelacoes" else valor)
            await s.commit()
            return _perfil(t)

    async def somar_jornada(self, pessoa_id: int, pontos: int, **campos) -> Perfil:
        """Soma no banco (não sobrescreve), para dois pontos ganhos ao mesmo tempo não se perderem."""
        async with self._sessoes() as s:
            await s.execute(update(PessoaTb).where(PessoaTb.id == pessoa_id)
                            .values(jornada=func.coalesce(PessoaTb.jornada, 0) + pontos, **campos))
            await s.commit()
        return await self.perfil(pessoa_id)

    async def definir_local(self, pessoa_id: int, lat: float, lon: float, cidade: Optional[str] = None) -> Perfil:
        async with self._sessoes() as s:
            t = await s.get(PessoaTb, pessoa_id)
            t.lat, t.lon, t.local_do_app = lat, lon, True
            if cidade:
                t.cidade = cidade
            await s.commit()
            return _perfil(t)

    async def candidatos_para(self, pessoa: Perfil, limite: int) -> List[Perfil]:
        """Os filtros baratos no banco; distância e o resto ficam com podem_se_ver (no domínio)."""
        reagidos = select(ReacaoTb.para_id).where(ReacaoTb.de_id == pessoa.id)
        com_conexao = select(MatchTb.b_id).where(MatchTb.a_id == pessoa.id).union(
            select(MatchTb.a_id).where(MatchTb.b_id == pessoa.id))
        denunciados = select(DenunciaTb.sobre_id).where(DenunciaTb.de_id == pessoa.id).union(
            select(DenunciaTb.de_id).where(DenunciaTb.sobre_id == pessoa.id))
        consulta = (select(PessoaTb).where(
            PessoaTb.elegivel.is_(True), PessoaTb.visivel.is_(True), PessoaTb.foto.is_not(None),
            PessoaTb.genero == pessoa.genero.oposto.value,
            PessoaTb.idade.between(pessoa.idade_min, pessoa.idade_max),
            PessoaTb.idade_min <= pessoa.idade, PessoaTb.idade_max >= pessoa.idade,
            PessoaTb.id.not_in(reagidos), PessoaTb.id.not_in(com_conexao), PessoaTb.id.not_in(denunciados))
            .order_by(PessoaTb.atualizado_em.desc()).limit(limite))
        async with self._sessoes() as s:
            return [_perfil(t) for t in (await s.execute(consulta)).scalars()]

    # ---------------- afinidades ----------------

    async def afinidades(self, pessoa_id: int, outros: Sequence[int]) -> Dict[int, Tuple[str, Afinidade]]:
        if not outros:
            return {}
        consulta = select(AfinidadeTb).where(or_(
            and_(AfinidadeTb.a_id == pessoa_id, AfinidadeTb.b_id.in_(list(outros))),
            and_(AfinidadeTb.b_id == pessoa_id, AfinidadeTb.a_id.in_(list(outros)))))
        async with self._sessoes() as s:
            saida = {}
            for t in (await s.execute(consulta)).scalars():
                outro = t.b_id if t.a_id == pessoa_id else t.a_id
                saida[outro] = (t.assinatura, Afinidade(nivel=Nivel(t.nivel), proximidade=Proximidade(t.proximidade),
                                                         apresentar=t.apresentar, em_comum=tuple(t.em_comum or ()),
                                                         origem=t.origem))
            return saida

    async def guardar_afinidades(self, pessoa_id: int, novas: Mapping[int, Tuple[str, Afinidade]]) -> None:
        if not novas:
            return
        async with self._sessoes() as s:
            for outro, (assinatura, a) in novas.items():
                a_id, b_id = par(pessoa_id, outro)
                t = await s.get(AfinidadeTb, (a_id, b_id))
                if t is None:
                    t = AfinidadeTb(a_id=a_id, b_id=b_id)
                    s.add(t)
                t.assinatura, t.nivel, t.proximidade = assinatura, a.nivel.value, a.proximidade.value
                t.apresentar, t.em_comum, t.origem = a.apresentar, list(a.em_comum), a.origem
            await s.commit()

    # ---------------- sinais do dia ----------------

    async def sinais_do_dia(self, pessoa_id: int, dia: str) -> Optional[List[SinalDoDia]]:
        """None = ainda não foram escolhidos hoje (lista vazia = escolhidos, mas não tinha ninguém)."""
        async with self._sessoes() as s:
            linhas = list((await s.execute(select(SugestaoTb).where(
                SugestaoTb.pessoa_id == pessoa_id, SugestaoTb.dia == dia).order_by(SugestaoTb.ordem))).scalars())
        if not linhas:
            return None
        return [SinalDoDia(t.outro_id, tuple(t.motivos or ())) for t in linhas if t.outro_id != pessoa_id]

    async def guardar_sinais_do_dia(self, pessoa_id: int, dia: str, sinais: Sequence[SinalDoDia]) -> None:
        async with self._sessoes() as s:
            # sem ninguém, guarda um marcador (a própria pessoa) para não procurar de novo a cada abertura
            linhas = [SugestaoTb(pessoa_id=pessoa_id, dia=dia, outro_id=x.outro_id, ordem=i, motivos=list(x.motivos))
                      for i, x in enumerate(sinais)] or [SugestaoTb(pessoa_id=pessoa_id, dia=dia, outro_id=pessoa_id)]
            s.add_all(linhas)
            try:
                await s.commit()
            except IntegrityError:          # duas abas abriram ao mesmo tempo: vale a primeira
                await s.rollback()

    async def esquecer_sinais_do_dia(self, pessoa_id: int, dia: str) -> None:
        async with self._sessoes() as s:
            await s.execute(delete(SugestaoTb).where(SugestaoTb.pessoa_id == pessoa_id, SugestaoTb.dia == dia))
            await s.commit()

    async def reagidos_por(self, pessoa_id: int) -> FrozenSet[int]:
        async with self._sessoes() as s:
            return frozenset((await s.execute(select(ReacaoTb.para_id).where(ReacaoTb.de_id == pessoa_id))).scalars())

    # ---------------- sinais e conexões ----------------

    async def reagir(self, de_id: int, para_id: int, curtiu: bool) -> Optional[Conexao]:
        async with self._sessoes() as s:
            t = await s.get(ReacaoTb, (de_id, para_id))
            if t is None:
                s.add(ReacaoTb(de_id=de_id, para_id=para_id, curtiu=curtiu))
            else:
                t.curtiu = curtiu
            await s.commit()
            if not curtiu:
                return None
            volta = await s.get(ReacaoTb, (para_id, de_id))
            if not (volta and volta.curtiu):
                return None
            a_id, b_id = par(de_id, para_id)
            existente = (await s.execute(select(MatchTb).where(MatchTb.a_id == a_id, MatchTb.b_id == b_id))
                         ).scalar_one_or_none()
            if existente:
                return _conexao(existente)
            nova = MatchTb(a_id=a_id, b_id=b_id, pontos=0, sintonia_soma=0.0, sintonia_qtd=0)
            s.add(nova)
            try:
                await s.commit()
            except IntegrityError:          # os dois enviaram ao mesmo tempo
                await s.rollback()
                return await self.conexao_entre(a_id, b_id)
            return _conexao(nova)

    async def conexoes_de(self, pessoa_id: int) -> List[Conexao]:
        consulta = (select(MatchTb).where(or_(MatchTb.a_id == pessoa_id, MatchTb.b_id == pessoa_id),
                                          MatchTb.desfeito_em.is_(None)).order_by(MatchTb.criado_em.desc()))
        async with self._sessoes() as s:
            return [_conexao(t) for t in (await s.execute(consulta)).scalars()]

    async def conexao(self, conexao_id: int) -> Optional[Conexao]:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, conexao_id)
            return _conexao(t) if t else None

    async def conexao_entre(self, a_id: int, b_id: int) -> Optional[Conexao]:
        a_id, b_id = par(a_id, b_id)
        async with self._sessoes() as s:
            t = (await s.execute(select(MatchTb).where(MatchTb.a_id == a_id, MatchTb.b_id == b_id))).scalar_one_or_none()
            return _conexao(t) if t else None

    async def registrar_evento(self, conexao_id: int, referencia: str, evento: EventoDaDupla) -> bool:
        """False se aquilo já tinha pontuado (cada conteúdo vale uma vez por dupla)."""
        async with self._sessoes() as s:
            s.add(EventoDaDuplaTb(conexao_id=conexao_id, referencia=referencia, tipo=evento.tipo,
                                  titulo=evento.titulo[:200], pontos=evento.pontos, sintonia=evento.sintonia))
            try:
                await s.flush()
            except IntegrityError:
                await s.rollback()
                return False
            await s.execute(update(MatchTb).where(MatchTb.id == conexao_id).values(
                pontos=func.coalesce(MatchTb.pontos, 0) + evento.pontos,
                sintonia_soma=func.coalesce(MatchTb.sintonia_soma, 0) + evento.sintonia,
                sintonia_qtd=func.coalesce(MatchTb.sintonia_qtd, 0) + 1))
            await s.commit()
            return True

    async def eventos(self, conexao_id: int, limite: int = 20) -> List[EventoDaDupla]:
        async with self._sessoes() as s:
            linhas = (await s.execute(select(EventoDaDuplaTb).where(EventoDaDuplaTb.conexao_id == conexao_id)
                                      .order_by(EventoDaDuplaTb.id.desc()).limit(limite))).scalars()
            return [_evento(t) for t in linhas]

    async def referencias(self, conexao_id: int) -> FrozenSet[str]:
        """O que já pontuou nessa conexão ("inicio", "conteudo:12", …)."""
        async with self._sessoes() as s:
            return frozenset((await s.execute(select(EventoDaDuplaTb.referencia).where(
                EventoDaDuplaTb.conexao_id == conexao_id))).scalars())

    async def tem_evento(self, conexao_id: int, referencia: str) -> bool:
        async with self._sessoes() as s:
            achado = (await s.execute(select(EventoDaDuplaTb.id).where(
                EventoDaDuplaTb.conexao_id == conexao_id, EventoDaDuplaTb.referencia == referencia))).first()
            return achado is not None

    async def eventos_de_hoje(self, conexao_id: int, tipo: str, dia: str) -> int:
        async with self._sessoes() as s:
            return (await s.execute(select(func.count()).select_from(EventoDaDuplaTb).where(
                EventoDaDuplaTb.conexao_id == conexao_id, EventoDaDuplaTb.tipo == tipo,
                EventoDaDuplaTb.criado_em >= _inicio_do_dia(dia)))).scalar_one()

    async def liberar(self, conexao_id: int, pessoa_id: int, item: str) -> None:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, conexao_id)
            if t.a_id == pessoa_id:
                t.liberados_a = sorted(set(t.liberados_a or ()) | {item})
            elif t.b_id == pessoa_id:
                t.liberados_b = sorted(set(t.liberados_b or ()) | {item})
            await s.commit()

    async def desfazer(self, conexao_id: int, pessoa_id: int) -> None:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, conexao_id)
            if t and t.desfeito_em is None:
                t.desfeito_em, t.desfeito_por = agora(), pessoa_id
                await s.commit()

    async def denunciar(self, de_id: int, sobre_id: int, motivo: str) -> None:
        async with self._sessoes() as s:
            s.add(DenunciaTb(de_id=de_id, sobre_id=sobre_id, motivo=(motivo or "")[:1000]))
            await s.commit()

    async def denuncias(self, limite: int = 100) -> List[dict]:
        async with self._sessoes() as s:
            linhas = (await s.execute(select(DenunciaTb).order_by(DenunciaTb.id.desc()).limit(limite))).scalars()
            return [{"id": t.id, "de_id": t.de_id, "sobre_id": t.sobre_id, "motivo": t.motivo,
                     "criado_em": t.criado_em.isoformat()} for t in linhas]

    # ---------------- mensagens ----------------

    async def mensagens(self, conexao_id: int, depois_de: int = 0, limite: int = 100) -> List[Mensagem]:
        if depois_de:
            consulta = (select(MensagemTb).where(MensagemTb.match_id == conexao_id, MensagemTb.id > depois_de)
                        .order_by(MensagemTb.id).limit(limite))
            async with self._sessoes() as s:
                return [_mensagem(t) for t in (await s.execute(consulta)).scalars()]
        # sem cursor: as últimas `limite`, em ordem
        consulta = (select(MensagemTb).where(MensagemTb.match_id == conexao_id).order_by(MensagemTb.id.desc())
                    .limit(limite))
        async with self._sessoes() as s:
            return [_mensagem(t) for t in reversed(list((await s.execute(consulta)).scalars()))]

    async def ultimas_mensagens(self, conexao_ids: Sequence[int]) -> Dict[int, Mensagem]:
        if not conexao_ids:
            return {}
        ultimas = (select(func.max(MensagemTb.id)).where(MensagemTb.match_id.in_(list(conexao_ids)))
                   .group_by(MensagemTb.match_id))
        async with self._sessoes() as s:
            linhas = (await s.execute(select(MensagemTb).where(MensagemTb.id.in_(ultimas)))).scalars()
            return {t.match_id: _mensagem(t) for t in linhas}

    async def nao_lidas(self, pessoa_id: int, lido_ate: Mapping[int, int]) -> Dict[int, int]:
        """Quantas mensagens da outra pessoa chegaram depois da última lida, por conexão."""
        if not lido_ate:
            return {}
        depois = or_(*(and_(MensagemTb.match_id == m, MensagemTb.id > ate) for m, ate in lido_ate.items()))
        consulta = (select(MensagemTb.match_id, func.count()).where(depois, MensagemTb.autor_id != pessoa_id)
                    .group_by(MensagemTb.match_id))
        async with self._sessoes() as s:
            return {m: n for m, n in (await s.execute(consulta)).all()}

    async def enviar(self, conexao_id: int, autor_id: int, texto: str) -> Mensagem:
        async with self._sessoes() as s:
            t = MensagemTb(match_id=conexao_id, autor_id=autor_id, texto=texto)
            s.add(t)
            await s.flush()
            conexao = await s.get(MatchTb, conexao_id)
            if conexao.a_id == autor_id:              # quem escreve já leu tudo até aqui
                conexao.lido_a = t.id
            else:
                conexao.lido_b = t.id
            await s.commit()
            return _mensagem(t)

    async def marcar_lido(self, conexao_id: int, pessoa_id: int, ate: int) -> None:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, conexao_id)
            if t.a_id == pessoa_id:
                t.lido_a = max(t.lido_a, ate)
            elif t.b_id == pessoa_id:
                t.lido_b = max(t.lido_b, ate)
            await s.commit()

    # ---------------- conteúdo e respostas ----------------

    async def salvar_conteudo(self, tipo: str, dados: Mapping, status: str, origem: str) -> Conteudo:
        async with self._sessoes() as s:
            t = ConteudoTb(tipo=tipo, dados=dict(dados), status=status, origem=origem,
                           decidido_em=agora() if status != "pendente" else None)
            s.add(t)
            await s.commit()
            return _conteudo(t)

    async def conteudo(self, conteudo_id: int) -> Optional[Conteudo]:
        async with self._sessoes() as s:
            t = await s.get(ConteudoTb, conteudo_id)
            return _conteudo(t) if t else None

    async def conteudos(self, tipo: Optional[str] = None, status: Optional[str] = None) -> List[Conteudo]:
        consulta = select(ConteudoTb).order_by(ConteudoTb.id)
        if tipo:
            consulta = consulta.where(ConteudoTb.tipo == tipo)
        if status:
            consulta = consulta.where(ConteudoTb.status == status)
        async with self._sessoes() as s:
            return [_conteudo(t) for t in (await s.execute(consulta)).scalars()]

    async def decidir_conteudo(self, conteudo_id: int, status: str, dados: Optional[Mapping] = None) -> Optional[Conteudo]:
        async with self._sessoes() as s:
            t = await s.get(ConteudoTb, conteudo_id)
            if not t:
                return None
            t.status, t.decidido_em = status, agora()
            if dados is not None:
                t.dados = dict(dados)
            await s.commit()
            return _conteudo(t)

    async def marcar_dia(self, conteudo_id: int, dia: str) -> None:
        async with self._sessoes() as s:
            await s.execute(update(ConteudoTb).where(ConteudoTb.id == conteudo_id).values(dia=dia))
            await s.commit()

    async def salvar_resposta(self, resposta: Resposta) -> bool:
        """False se já tinha respondido (a primeira resposta é a que vale)."""
        async with self._sessoes() as s:
            s.add(RespostaTb(pessoa_id=resposta.pessoa_id, conteudo_id=resposta.conteudo_id, dados=dict(resposta.dados),
                             temas=list(resposta.temas)))
            try:
                await s.commit()
            except IntegrityError:
                await s.rollback()
                return False
            return True

    async def resposta(self, pessoa_id: int, conteudo_id: int) -> Optional[Resposta]:
        async with self._sessoes() as s:
            t = await s.get(RespostaTb, (pessoa_id, conteudo_id))
            return _resposta(t) if t else None

    async def respostas(self, pessoa_ids: Sequence[int], conteudo_ids: Optional[Sequence[int]] = None) -> List[Resposta]:
        if not pessoa_ids:
            return []
        consulta = select(RespostaTb).where(RespostaTb.pessoa_id.in_(list(pessoa_ids)))
        if conteudo_ids is not None:
            consulta = consulta.where(RespostaTb.conteudo_id.in_(list(conteudo_ids)))
        async with self._sessoes() as s:
            return [_resposta(t) for t in (await s.execute(consulta)).scalars()]

    async def contagem_de_respostas(self, pessoa_id: int) -> Dict[str, int]:
        consulta = (select(ConteudoTb.tipo, func.count()).join(RespostaTb, RespostaTb.conteudo_id == ConteudoTb.id)
                    .where(RespostaTb.pessoa_id == pessoa_id).group_by(ConteudoTb.tipo))
        async with self._sessoes() as s:
            return {tipo: n for tipo, n in (await s.execute(consulta)).all()}
