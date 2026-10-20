"""Portas: o que os casos de uso precisam do mundo de fora (CRM, IA, banco). As implementações ficam em infraestrutura/."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Mapping, Optional, Protocol, Sequence, Tuple

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


class Escritor(Protocol):
    """Modelo de texto que escreve conteúdo novo (devocionais, perguntas, testes), sempre em JSON."""
    async def escrever(self, instrucao: str, pedido: str) -> dict: ...


class Diretorio(Protocol):
    """O CRM (só leitura)."""
    async def candidatas(self, variantes_do_cpf: Sequence[str]) -> Sequence[Candidata]: ...
    async def dados(self, igreja_id: str, membro_id: str) -> Optional[DadosDoCrm]: ...


@dataclass(frozen=True)
class Conexao:
    """Os dois enviaram sinal. Os pontos e a sintonia vêm dos eventos da dupla."""
    id: int
    a_id: int
    b_id: int
    criado_em: str
    pontos: int
    sintonia: Optional[float]                      # média 0..1 de tudo que a dupla comparou
    liberados: Mapping[int, FrozenSet[str]]        # pessoa → itens liberados na mão
    lido_ate: Mapping[int, int]                    # pessoa → última mensagem lida
    desfeita: bool = False

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


@dataclass(frozen=True)
class Conteudo:
    id: int
    tipo: str                 # devocional, pergunta, teste
    status: str               # pendente, aprovado, recusado
    origem: str               # ia, semente
    dados: Mapping
    dia: Optional[str] = None
    criado_em: str = ""

    @property
    def titulo(self) -> str:
        d = self.dados
        return str(d.get("titulo") or d.get("texto") or d.get("referencia") or "")


@dataclass(frozen=True)
class Resposta:
    pessoa_id: int
    conteudo_id: int
    dados: Mapping
    temas: Tuple[str, ...] = ()
    criado_em: str = ""


@dataclass(frozen=True)
class EventoDaDupla:
    tipo: str
    titulo: str
    pontos: int
    sintonia: float
    criado_em: str = ""


@dataclass(frozen=True)
class SinalDoDia:
    outro_id: int
    motivos: Tuple[str, ...] = field(default_factory=tuple)


class Repositorio(Protocol):
    # perfis
    async def salvar_do_crm(self, dados: DadosDoCrm) -> Perfil: ...
    async def marcar_inelegivel(self, igreja_id: str, membro_id: str) -> None: ...
    async def perfil(self, pessoa_id: int) -> Optional[Perfil]: ...
    async def perfis(self, ids: Sequence[int]) -> Dict[int, Perfil]: ...
    async def atualizar_perfil(self, pessoa_id: int, **campos) -> Perfil: ...
    async def somar_jornada(self, pessoa_id: int, pontos: int, **campos) -> Perfil: ...
    async def definir_local(self, pessoa_id: int, lat: float, lon: float, cidade: Optional[str] = None) -> Perfil: ...
    async def candidatos_para(self, pessoa: Perfil, limite: int) -> List[Perfil]: ...
    # afinidade de hobbies e localização (cache do JEV)
    async def afinidades(self, pessoa_id: int, outros: Sequence[int]) -> Dict[int, Tuple[str, Afinidade]]: ...
    async def guardar_afinidades(self, pessoa_id: int, novas: Mapping[int, Tuple[str, Afinidade]]) -> None: ...
    # sinais e conexões
    async def sinais_do_dia(self, pessoa_id: int, dia: str) -> Optional[List[SinalDoDia]]: ...
    async def guardar_sinais_do_dia(self, pessoa_id: int, dia: str, sinais: Sequence[SinalDoDia]) -> None: ...
    async def esquecer_sinais_do_dia(self, pessoa_id: int, dia: str) -> None: ...
    async def reagidos_por(self, pessoa_id: int) -> FrozenSet[int]: ...
    async def reagir(self, de_id: int, para_id: int, curtiu: bool) -> Optional[Conexao]: ...
    async def conexoes_de(self, pessoa_id: int) -> List[Conexao]: ...
    async def conexao(self, conexao_id: int) -> Optional[Conexao]: ...
    async def conexao_entre(self, a_id: int, b_id: int) -> Optional[Conexao]: ...
    async def registrar_evento(self, conexao_id: int, referencia: str, evento: EventoDaDupla) -> bool: ...
    async def eventos(self, conexao_id: int, limite: int = 20) -> List[EventoDaDupla]: ...
    async def tem_evento(self, conexao_id: int, referencia: str) -> bool: ...
    async def referencias(self, conexao_id: int) -> FrozenSet[str]: ...
    async def eventos_de_hoje(self, conexao_id: int, tipo: str, dia: str) -> int: ...
    async def liberar(self, conexao_id: int, pessoa_id: int, item: str) -> None: ...
    async def desfazer(self, conexao_id: int, pessoa_id: int) -> None: ...
    async def denunciar(self, de_id: int, sobre_id: int, motivo: str) -> None: ...
    async def denuncias(self, limite: int = 100) -> List[dict]: ...
    # mensagens
    async def mensagens(self, conexao_id: int, depois_de: int = 0, limite: int = 100) -> List[Mensagem]: ...
    async def ultimas_mensagens(self, conexao_ids: Sequence[int]) -> Dict[int, Mensagem]: ...
    async def nao_lidas(self, pessoa_id: int, lido_ate: Mapping[int, int]) -> Dict[int, int]: ...
    async def enviar(self, conexao_id: int, autor_id: int, texto: str) -> Mensagem: ...
    async def marcar_lido(self, conexao_id: int, pessoa_id: int, ate: int) -> None: ...
    # conteúdo e respostas
    async def salvar_conteudo(self, tipo: str, dados: Mapping, status: str, origem: str) -> Conteudo: ...
    async def conteudo(self, conteudo_id: int) -> Optional[Conteudo]: ...
    async def conteudos(self, tipo: Optional[str] = None, status: Optional[str] = None) -> List[Conteudo]: ...
    async def decidir_conteudo(self, conteudo_id: int, status: str, dados: Optional[Mapping] = None) -> Optional[Conteudo]: ...
    async def marcar_dia(self, conteudo_id: int, dia: str) -> None: ...
    async def salvar_resposta(self, resposta: Resposta) -> bool: ...
    async def resposta(self, pessoa_id: int, conteudo_id: int) -> Optional[Resposta]: ...
    async def respostas(self, pessoa_ids: Sequence[int], conteudo_ids: Optional[Sequence[int]] = None) -> List[Resposta]: ...
    async def contagem_de_respostas(self, pessoa_id: int) -> Dict[str, int]: ...


class Bots(Protocol):
    """Só no modo demonstração: os perfis de teste "jogam" sozinhos para dar para testar sem gente de verdade."""
    async def ao_entrar(self, pessoa: Perfil) -> None: ...
    async def ao_enviar_sinal(self, de: Perfil, para: Perfil) -> None: ...
    async def responder_se_preciso(self, bot: Perfil, conteudo: Conteudo) -> None: ...
    async def ao_receber_mensagem(self, conexao: Conexao, bot: Perfil) -> None: ...
