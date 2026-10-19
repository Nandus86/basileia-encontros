"""Portas: o que os casos de uso precisam do mundo de fora (CRM, IA, banco). As implementações ficam em infraestrutura/."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Protocol, Sequence, Tuple

from encontros.dominio.afinidade import Afinidade
from encontros.dominio.perfil import DadosDoCrm, Perfil


@dataclass(frozen=True)
class Pergunta:
    """Pergunta fechada para o JEV: uma instrução e as opções (chave → critério)."""
    instrucao: str
    opcoes: Mapping[str, str]


@dataclass(frozen=True)
class Candidata:
    """Um cadastro achado pelo CPF (a pessoa pode estar em mais de uma igreja)."""
    membro_id: str
    igreja_id: str
    igreja_nome: str
    nome: str


@dataclass(frozen=True)
class Julgamento:
    respostas: Mapping[str, str]       # pergunta → opção escolhida (sempre uma das opções)
    origem: str                        # jev ou llm (a reserva)


class Julgador(Protocol):
    async def julgar(self, estado: str, perguntas: Mapping[str, Pergunta]) -> Julgamento: ...


class Diretorio(Protocol):
    """O CRM (só leitura)."""
    async def candidatas(self, variantes_do_cpf: Sequence[str]) -> Sequence[Candidata]: ...
    async def dados(self, igreja_id: str, membro_id: str) -> Optional[DadosDoCrm]: ...


@dataclass(frozen=True)
class Match:
    id: int
    a_id: int
    b_id: int
    criado_em: str
    foto_liberada: Mapping[int, bool]      # pessoa → liberou a própria foto
    lido_ate: Mapping[int, int]            # pessoa → última mensagem lida
    desfeito: bool = False

    def outra(self, pessoa_id: int) -> int:
        return self.b_id if pessoa_id == self.a_id else self.a_id

    def tem(self, pessoa_id: int) -> bool:
        return pessoa_id in (self.a_id, self.b_id)


@dataclass(frozen=True)
class Mensagem:
    id: int
    match_id: int
    autor_id: int
    texto: str
    criado_em: str


class Repositorio(Protocol):
    async def salvar_do_crm(self, dados: DadosDoCrm) -> Perfil: ...
    async def marcar_inelegivel(self, igreja_id: str, membro_id: str) -> None: ...
    async def perfil(self, pessoa_id: int) -> Optional[Perfil]: ...
    async def perfis(self, ids: Sequence[int]) -> Dict[int, Perfil]: ...
    async def atualizar_perfil(self, pessoa_id: int, **campos) -> Perfil: ...
    async def candidatos_para(self, pessoa: Perfil, limite: int) -> List[Perfil]: ...
    async def afinidades(self, pessoa_id: int, outros: Sequence[int]) -> Dict[int, Tuple[str, Afinidade]]: ...
    async def guardar_afinidades(self, pessoa_id: int, novas: Mapping[int, Tuple[str, Afinidade]]) -> None: ...
    async def reagir(self, de_id: int, para_id: int, curtiu: bool) -> Optional[Match]: ...
    async def matches_de(self, pessoa_id: int) -> List[Match]: ...
    async def match(self, match_id: int) -> Optional[Match]: ...
    async def match_entre(self, a_id: int, b_id: int) -> Optional[Match]: ...
    async def mensagens(self, match_id: int, depois_de: int = 0, limite: int = 100) -> List[Mensagem]: ...
    async def ultimas_mensagens(self, match_ids: Sequence[int]) -> Dict[int, Mensagem]: ...
    async def nao_lidas(self, pessoa_id: int, lido_ate: Mapping[int, int]) -> Dict[int, int]: ...
    async def enviar(self, match_id: int, autor_id: int, texto: str) -> Mensagem: ...
    async def marcar_lido(self, match_id: int, pessoa_id: int, ate: int) -> None: ...
    async def liberar_foto(self, match_id: int, pessoa_id: int) -> None: ...
    async def desfazer(self, match_id: int, pessoa_id: int) -> None: ...
    async def denunciar(self, de_id: int, sobre_id: int, motivo: str) -> None: ...
    async def definir_local(self, pessoa_id: int, lat: float, lon: float, cidade: Optional[str] = None) -> Perfil: ...
