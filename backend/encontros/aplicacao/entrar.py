"""Caso de uso: entrar no app com o cadastro da igreja.

Mesmo acesso do app de conversa (mensageiro): usuário e senha são o CPF do cadastro, conferido no CRM.
PROVISÓRIO e fraco (quem souber o CPF entra) até combinar uma senha de verdade com o dev do CRM —
por isso as tentativas são limitadas, o erro é sempre o mesmo e só as igrejas liberadas entram.

A cada entrada os dados do CRM são lidos de novo: quem casou, ficou desativado ou mudou de cadastro
deixa de aparecer na hora.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from encontros.aplicacao.portas import Candidata, Diretorio, Repositorio
from encontros.dominio.perfil import Perfil, motivo_para_nao_entrar

NAO_ENCONTRADO = "Usuário ou senha não conferem com o cadastro da igreja."
MUITAS_TENTATIVAS = "Muitas tentativas. Espere alguns minutos e tente de novo."
IGREJA_FORA = "O app ainda não está liberado para a sua igreja."


def digitos(texto: object) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def cpf_valido(cpf: str) -> bool:
    """Confere os dígitos verificadores e recusa os de preenchimento (000.000.000-00, 111.111.111-11…)."""
    d = digitos(cpf)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        if (soma * 10 % 11) % 10 != int(d[tamanho]):
            return False
    return True


def variantes_do_cpf(cpf: str) -> List[str]:
    """Como o CPF pode estar gravado no CRM: 11 dígitos, formatado ou sem o zero da frente."""
    d = digitos(cpf)
    if not cpf_valido(d):
        return []
    return list(dict.fromkeys([d, f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}", f"{d[:9]}-{d[9:]}", d.lstrip("0")]))


@dataclass(frozen=True)
class Liberacao:
    """Quais igrejas podem usar o app ("*" = todas)."""
    igrejas: FrozenSet[str] = frozenset()

    @classmethod
    def de_texto(cls, texto: str) -> "Liberacao":
        return cls(frozenset(p.strip() for p in (texto or "").split(",") if p.strip()))

    def permite(self, igreja_id: str) -> bool:
        return "*" in self.igrejas or igreja_id in self.igrejas


class LimiteDeTentativas:
    """Em memória: o MVP roda numa cópia só. Com várias réplicas, trocar por um contador no Redis."""

    def __init__(self, tentativas: int = 8, janela_segundos: int = 900):
        self._tentativas = tentativas
        self._janela = janela_segundos
        self._registro: Dict[str, Tuple[float, int]] = {}

    def permitir(self, chave: str) -> bool:
        agora = time.monotonic()
        inicio, contagem = self._registro.get(chave, (agora, 0))
        if agora - inicio > self._janela:
            inicio, contagem = agora, 0
        self._registro[chave] = (inicio, contagem + 1)
        return contagem < self._tentativas


@dataclass(frozen=True)
class ResultadoDaEntrada:
    perfil: Optional[Perfil] = None
    escolher: List[Candidata] = field(default_factory=list)   # mais de uma igreja: a pessoa escolhe
    erro: Optional[str] = None


class Entrar:
    def __init__(self, diretorio: Diretorio, repositorio: Repositorio, liberacao: Liberacao,
                 estados_civis: FrozenSet[str], idade_minima: int, limites: Optional[LimiteDeTentativas] = None):
        self._diretorio = diretorio
        self._repo = repositorio
        self._liberacao = liberacao
        self._estados_civis = estados_civis
        self._idade_minima = idade_minima
        self._limites = limites or LimiteDeTentativas()

    async def executar(self, usuario: str, senha: str, origem: str, igreja_id: Optional[str] = None) -> ResultadoDaEntrada:
        cpf = digitos(usuario)
        if not all(self._limites.permitir(c) for c in (f"origem:{origem}", f"cpf:{cpf}")):
            return ResultadoDaEntrada(erro=MUITAS_TENTATIVAS)
        variantes = variantes_do_cpf(cpf)
        if not variantes or digitos(senha) != cpf:          # por enquanto a senha é o próprio CPF
            return ResultadoDaEntrada(erro=NAO_ENCONTRADO)
        achadas = list(await self._diretorio.candidatas(variantes))
        if not achadas:
            return ResultadoDaEntrada(erro=NAO_ENCONTRADO)
        liberadas = [c for c in achadas if self._liberacao.permite(c.igreja_id)]
        if not liberadas:
            return ResultadoDaEntrada(erro=IGREJA_FORA)
        if igreja_id:
            liberadas = [c for c in liberadas if c.igreja_id == igreja_id]
            if not liberadas:
                return ResultadoDaEntrada(erro=NAO_ENCONTRADO)
        if len({c.igreja_id for c in liberadas}) > 1:
            return ResultadoDaEntrada(escolher=sorted(liberadas, key=lambda c: c.igreja_nome))
        return await self._abrir(liberadas[0])

    async def _abrir(self, candidata: Candidata) -> ResultadoDaEntrada:
        dados = await self._diretorio.dados(candidata.igreja_id, candidata.membro_id)
        if not dados:
            return ResultadoDaEntrada(erro=NAO_ENCONTRADO)
        motivo = motivo_para_nao_entrar(dados, self._estados_civis, self._idade_minima)
        if motivo:
            # se já usava o app e deixou de poder (casou, foi desativado…), sai do Descobrir na hora
            await self._repo.marcar_inelegivel(dados.igreja_id, dados.membro_id)
            return ResultadoDaEntrada(erro=motivo)
        return ResultadoDaEntrada(perfil=await self._repo.salvar_do_crm(dados))
