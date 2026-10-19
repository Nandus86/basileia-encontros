"""Implementa a porta Repositorio com SQLAlchemy (Postgres ou SQLite)."""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from encontros.aplicacao.portas import Match, Mensagem
from encontros.dominio.afinidade import Afinidade, Nivel, Proximidade, par
from encontros.dominio.perfil import DadosDoCrm, Genero, Perfil
from encontros.infraestrutura.banco import (AfinidadeTb, DenunciaTb, MatchTb, MensagemTb, PessoaTb, ReacaoTb,
                                            agora)

CAMPOS_EDITAVEIS = {"hobbies", "bio", "idade_min", "idade_max", "raio_km", "visivel", "foto"}


def _perfil(t: PessoaTb) -> Perfil:
    return Perfil(id=t.id, membro_id=t.membro_id, igreja_id=t.igreja_id, igreja_nome=t.igreja_nome, nome=t.nome,
                  genero=Genero(t.genero), idade=t.idade, cidade=t.cidade, bairro=t.bairro,
                  coordenadas=(t.lat, t.lon) if t.lat is not None and t.lon is not None else None,
                  hobbies=tuple(t.hobbies or ()), bio=t.bio or "", tem_foto=bool(t.foto), idade_min=t.idade_min,
                  idade_max=t.idade_max, raio_km=t.raio_km, visivel=t.visivel, elegivel=t.elegivel,
                  extras={"foto": t.foto, "local_do_app": t.local_do_app})


def _match(t: MatchTb) -> Match:
    return Match(id=t.id, a_id=t.a_id, b_id=t.b_id, criado_em=t.criado_em.isoformat(),
                 foto_liberada={t.a_id: t.foto_a, t.b_id: t.foto_b}, lido_ate={t.a_id: t.lido_a, t.b_id: t.lido_b},
                 desfeito=t.desfeito_em is not None)


def _mensagem(t: MensagemTb) -> Mensagem:
    return Mensagem(id=t.id, match_id=t.match_id, autor_id=t.autor_id, texto=t.texto, criado_em=t.criado_em.isoformat())


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
                    setattr(t, nome, list(valor) if nome == "hobbies" else valor)
            await s.commit()
            return _perfil(t)

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
        com_match = select(MatchTb.b_id).where(MatchTb.a_id == pessoa.id).union(
            select(MatchTb.a_id).where(MatchTb.b_id == pessoa.id))
        denunciados = select(DenunciaTb.sobre_id).where(DenunciaTb.de_id == pessoa.id).union(
            select(DenunciaTb.de_id).where(DenunciaTb.sobre_id == pessoa.id))
        consulta = (select(PessoaTb).where(
            PessoaTb.elegivel.is_(True), PessoaTb.visivel.is_(True), PessoaTb.foto.is_not(None),
            PessoaTb.genero == pessoa.genero.oposto.value,
            PessoaTb.idade.between(pessoa.idade_min, pessoa.idade_max),
            PessoaTb.idade_min <= pessoa.idade, PessoaTb.idade_max >= pessoa.idade,
            PessoaTb.id.not_in(reagidos), PessoaTb.id.not_in(com_match), PessoaTb.id.not_in(denunciados))
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

    # ---------------- curtidas e matches ----------------

    async def reagir(self, de_id: int, para_id: int, curtiu: bool) -> Optional[Match]:
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
                return _match(existente)
            novo = MatchTb(a_id=a_id, b_id=b_id)
            s.add(novo)
            try:
                await s.commit()
            except IntegrityError:          # os dois curtiram ao mesmo tempo
                await s.rollback()
                return await self.match_entre(a_id, b_id)
            return _match(novo)

    async def matches_de(self, pessoa_id: int) -> List[Match]:
        consulta = (select(MatchTb).where(or_(MatchTb.a_id == pessoa_id, MatchTb.b_id == pessoa_id),
                                          MatchTb.desfeito_em.is_(None)).order_by(MatchTb.criado_em.desc()))
        async with self._sessoes() as s:
            return [_match(t) for t in (await s.execute(consulta)).scalars()]

    async def match(self, match_id: int) -> Optional[Match]:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, match_id)
            return _match(t) if t else None

    async def match_entre(self, a_id: int, b_id: int) -> Optional[Match]:
        a_id, b_id = par(a_id, b_id)
        async with self._sessoes() as s:
            t = (await s.execute(select(MatchTb).where(MatchTb.a_id == a_id, MatchTb.b_id == b_id))).scalar_one_or_none()
            return _match(t) if t else None

    async def liberar_foto(self, match_id: int, pessoa_id: int) -> None:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, match_id)
            if t.a_id == pessoa_id:
                t.foto_a = True
            elif t.b_id == pessoa_id:
                t.foto_b = True
            await s.commit()

    async def desfazer(self, match_id: int, pessoa_id: int) -> None:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, match_id)
            if t and t.desfeito_em is None:
                t.desfeito_em, t.desfeito_por = agora(), pessoa_id
                await s.commit()

    async def denunciar(self, de_id: int, sobre_id: int, motivo: str) -> None:
        async with self._sessoes() as s:
            s.add(DenunciaTb(de_id=de_id, sobre_id=sobre_id, motivo=(motivo or "")[:1000]))
            await s.commit()

    # ---------------- mensagens ----------------

    async def mensagens(self, match_id: int, depois_de: int = 0, limite: int = 100) -> List[Mensagem]:
        if depois_de:
            consulta = (select(MensagemTb).where(MensagemTb.match_id == match_id, MensagemTb.id > depois_de)
                        .order_by(MensagemTb.id).limit(limite))
            async with self._sessoes() as s:
                return [_mensagem(t) for t in (await s.execute(consulta)).scalars()]
        # sem cursor: as últimas `limite`, em ordem
        consulta = (select(MensagemTb).where(MensagemTb.match_id == match_id).order_by(MensagemTb.id.desc())
                    .limit(limite))
        async with self._sessoes() as s:
            return [_mensagem(t) for t in reversed(list((await s.execute(consulta)).scalars()))]

    async def ultimas_mensagens(self, match_ids: Sequence[int]) -> Dict[int, Mensagem]:
        if not match_ids:
            return {}
        ultimas = (select(func.max(MensagemTb.id)).where(MensagemTb.match_id.in_(list(match_ids)))
                   .group_by(MensagemTb.match_id))
        async with self._sessoes() as s:
            linhas = (await s.execute(select(MensagemTb).where(MensagemTb.id.in_(ultimas)))).scalars()
            return {t.match_id: _mensagem(t) for t in linhas}

    async def nao_lidas(self, pessoa_id: int, lido_ate: Mapping[int, int]) -> Dict[int, int]:
        """Quantas mensagens da outra pessoa chegaram depois da última lida, por match."""
        if not lido_ate:
            return {}
        depois = or_(*(and_(MensagemTb.match_id == m, MensagemTb.id > ate) for m, ate in lido_ate.items()))
        consulta = (select(MensagemTb.match_id, func.count()).where(depois, MensagemTb.autor_id != pessoa_id)
                    .group_by(MensagemTb.match_id))
        async with self._sessoes() as s:
            return {m: n for m, n in (await s.execute(consulta)).all()}

    async def enviar(self, match_id: int, autor_id: int, texto: str) -> Mensagem:
        async with self._sessoes() as s:
            t = MensagemTb(match_id=match_id, autor_id=autor_id, texto=texto)
            s.add(t)
            await s.flush()
            casado = await s.get(MatchTb, match_id)
            if casado.a_id == autor_id:              # quem escreve já leu tudo até aqui
                casado.lido_a = t.id
            else:
                casado.lido_b = t.id
            await s.commit()
            return _mensagem(t)

    async def marcar_lido(self, match_id: int, pessoa_id: int, ate: int) -> None:
        async with self._sessoes() as s:
            t = await s.get(MatchTb, match_id)
            if t.a_id == pessoa_id:
                t.lido_a = max(t.lido_a, ate)
            elif t.b_id == pessoa_id:
                t.lido_b = max(t.lido_b, ate)
            await s.commit()
