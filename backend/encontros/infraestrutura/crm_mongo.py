"""Cadastro da igreja no Mongo do CRM — só leitura, pedindo só os campos necessários
(mesmo acesso e mesmas conversões do Motor de Cuidado e do mensageiro)."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Optional, Sequence, Tuple

from bson import ObjectId
from pymongo import AsyncMongoClient, ReadPreference

from encontros.aplicacao.portas import Candidata
from encontros.dominio.perfil import (DadosDoCrm, TipoDePessoa, estado_civil_de, idade_em, normalizar_genero)

CAMPOS_PESSOA = {"church_id": 1, "fullname": 1, "name": 1, "role": 1, "visitant": 1, "gender": 1,
                 "birthday_date": 1, "marital_status": 1, "family.spouse": 1, "address.latitude": 1,
                 "address.longitude": 1, "address.neighborhood": 1, "address.city": 1, "additional.blocked": 1}


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _oid(valor: str) -> Optional[ObjectId]:
    return ObjectId(valor) if ObjectId.is_valid(str(valor)) else None


def _coordenadas(endereco: Any) -> Optional[Tuple[float, float]]:
    try:
        lat, lon = float(endereco["latitude"]), float(endereco["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    return (lat, lon) if lat and lon and -90 <= lat <= 90 and -180 <= lon <= 180 else None


def dados_de(doc: Mapping[str, Any], igreja_nome: str, hoje: date) -> DadosDoCrm:
    """O cadastro do CRM → o que o app precisa. Quem é "contact" ou visitante não é membro."""
    papel = _texto(doc.get("role")).lower()
    if doc.get("visitant") is True or "visitant" in papel:
        tipo = TipoDePessoa.VISITANTE
    elif papel == "contact":
        tipo = TipoDePessoa.CONTATO
    else:
        tipo = TipoDePessoa.MEMBRO
    estado = estado_civil_de(doc.get("marital_status"))
    conjuge = ((doc.get("family") or {}).get("spouse")) or {}
    if estado in (None, "solteiro") and isinstance(conjuge, dict) and (conjuge.get("id_member") or conjuge.get("fullname")):
        estado = "casado"       # tem cônjuge ligado no cadastro: não é solteiro, diga o campo o que disser
    endereco = doc.get("address") or {}
    return DadosDoCrm(
        membro_id=str(doc["_id"]), igreja_id=_texto(doc.get("church_id")), igreja_nome=igreja_nome,
        nome=_texto(doc.get("fullname") or doc.get("name")), tipo=tipo, genero=normalizar_genero(doc.get("gender")),
        idade=idade_em(doc.get("birthday_date"), hoje), estado_civil=estado,
        cidade=_texto(endereco.get("city")), bairro=_texto(endereco.get("neighborhood")),
        coordenadas=_coordenadas(endereco),
        desativado=papel.startswith("disabled") or (doc.get("additional") or {}).get("blocked") is True)


class DiretorioMongo:
    def __init__(self, uri: str, banco: str):
        self._cliente = AsyncMongoClient(uri, read_preference=ReadPreference.SECONDARY_PREFERRED,
                                         appname="basile-encontros", serverSelectionTimeoutMS=15000)
        self._db = self._cliente[banco]

    async def _nomes_das_igrejas(self, ids: Sequence[str]) -> dict:
        oids = [o for o in {_oid(i) for i in ids} if o]
        return {str(c["_id"]): _texto(c.get("church_name"))
                async for c in self._db.churches.find({"_id": {"$in": oids}}, {"church_name": 1})}

    async def candidatas(self, variantes_do_cpf: Sequence[str]) -> Sequence[Candidata]:
        if not variantes_do_cpf:
            return []
        docs = await self._db.members.find({"document": {"$in": list(variantes_do_cpf)}},
                                           {"fullname": 1, "name": 1, "church_id": 1, "role": 1}).to_list(50)
        docs = [d for d in docs if d.get("church_id") and not _texto(d.get("role")).lower().startswith("disabled")]
        nomes = await self._nomes_das_igrejas([_texto(d.get("church_id")) for d in docs])
        return [Candidata(membro_id=str(d["_id"]), igreja_id=_texto(d.get("church_id")),
                          igreja_nome=nomes.get(_texto(d.get("church_id")), ""),
                          nome=_texto(d.get("fullname") or d.get("name"))) for d in docs]

    async def dados(self, igreja_id: str, membro_id: str) -> Optional[DadosDoCrm]:
        oid = _oid(membro_id)
        doc = await self._db.members.find_one({"_id": oid, "church_id": igreja_id}, CAMPOS_PESSOA) if oid else None
        if not doc:
            return None
        nomes = await self._nomes_das_igrejas([igreja_id])
        return dados_de(doc, nomes.get(igreja_id, ""), date.today())

    async def fechar(self) -> None:
        await self._cliente.close()
