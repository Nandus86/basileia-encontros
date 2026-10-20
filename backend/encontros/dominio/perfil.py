"""Quem pode usar o app e como a pessoa aparece para os outros (regras puras, sem banco nem rede)."""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date
from enum import Enum
from typing import FrozenSet, Optional, Tuple

IDADE_MINIMA = 18
HOBBIES_MINIMOS = 3
HOBBIES_MAXIMOS = 10
TAMANHO_BIO = 300

# Catálogo fechado: hobbies iguais se comparam sem IA; os parecidos ("Corrida" e "Academia") ficam para o JEV
HOBBIES: Tuple[str, ...] = (
    "Louvor e música", "Tocar instrumento", "Leitura bíblica", "Leitura", "Estudos teológicos", "Missões",
    "Voluntariado", "Ministério infantil", "Teatro e dança", "Futebol", "Vôlei", "Corrida", "Academia",
    "Ciclismo", "Trilhas e natureza", "Praia", "Viagens", "Cozinhar", "Café", "Cinema e séries", "Games",
    "Fotografia", "Artes e desenho", "Tecnologia", "Idiomas", "Pets", "Jardinagem", "Empreender",
)


class Genero(str, Enum):
    FEMININO = "feminino"
    MASCULINO = "masculino"

    @property
    def oposto(self) -> "Genero":
        return Genero.MASCULINO if self == Genero.FEMININO else Genero.FEMININO


class TipoDePessoa(str, Enum):
    MEMBRO = "membro"
    VISITANTE = "visitante"
    CONTATO = "contato"


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().strip().lower()


def normalizar_genero(valor: object) -> Optional[Genero]:
    """O CRM grava de vários jeitos: FEMININO, Feminino, Femenino, F, FEMALE, MASCULINO, M, MALE…"""
    texto = sem_acento(str(valor or ""))
    if texto in ("f", "fem", "feminino", "femenino", "female", "mulher"):
        return Genero.FEMININO
    if texto in ("m", "masc", "masculino", "male", "homem"):
        return Genero.MASCULINO
    return None


def idade_em(aniversario: object, hoje: date) -> Optional[int]:
    """Idade a partir de AAAA-MM-DD, DD/MM/AAAA ou DD-MM-AAAA (os três formatos que aparecem no CRM)."""
    texto = str(aniversario or "").strip()[:10]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", texto)
    if m:
        ano, mes, dia = int(m[1]), int(m[2]), int(m[3])
    else:
        m = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})$", texto)
        if not m:
            return None
        dia, mes, ano = int(m[1]), int(m[2]), int(m[3])
    try:
        nascimento = date(ano, mes, dia)
    except ValueError:
        return None
    idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    return idade if 0 <= idade <= 120 else None


_ESTADOS = (("uniao_estavel", ("uniao",)), ("casado", ("casad", "married")), ("solteiro", ("solteir", "single")),
            ("divorciado", ("divorciad", "divorced")), ("separado", ("separad",)), ("viuvo", ("viuv", "widow")))


def estado_civil_de(valor: object) -> Optional[str]:
    """casado, solteiro, divorciado, separado, uniao_estavel ou viuvo (os mesmos nomes do Motor de Cuidado)."""
    texto = sem_acento(str(valor or ""))
    for estado, comecos in _ESTADOS:
        if any(texto.startswith(c) or (c == "uniao" and c in texto) for c in comecos):
            return estado
    return None


def primeiro_nome(nome: str) -> str:
    """Para os outros aparece só o primeiro nome (o sobrenome identificaria a família na igreja)."""
    partes = (nome or "").split()
    return partes[0].capitalize() if partes else ""


def distancia_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def distancia_aproximada(km: Optional[float]) -> Optional[int]:
    """O que aparece no cartão: "a ~5 km", nunca a distância exata (daria para triangular o endereço)."""
    if km is None:
        return None
    if km < 5:
        return 5
    return int(math.ceil(km / 5.0) * 5)


@dataclass(frozen=True)
class DadosDoCrm:
    """O cadastro da pessoa na igreja (lido do CRM a cada entrada)."""
    membro_id: str
    igreja_id: str
    igreja_nome: str
    nome: str
    tipo: TipoDePessoa
    genero: Optional[Genero] = None
    idade: Optional[int] = None
    estado_civil: Optional[str] = None
    cidade: str = ""
    bairro: str = ""
    coordenadas: Optional[Tuple[float, float]] = None
    desativado: bool = False


def motivo_para_nao_entrar(dados: DadosDoCrm, estados_civis: FrozenSet[str], idade_minima: int = IDADE_MINIMA) -> Optional[str]:
    """None = pode usar o app. Senão, o motivo em linguagem simples (aparece na tela de entrada)."""
    if dados.desativado or dados.tipo != TipoDePessoa.MEMBRO:
        return "O app é só para membros da igreja."
    if dados.idade is None:
        return "Sua data de nascimento não está no cadastro da igreja. Peça para a secretaria atualizar."
    if dados.idade < idade_minima:
        return f"O app é só para maiores de {idade_minima} anos."
    if dados.estado_civil is None:
        return "Seu estado civil não está no cadastro da igreja. Peça para a secretaria atualizar."
    if dados.estado_civil not in estados_civis:
        return "O app é só para solteiros. Se o seu estado civil mudou, peça para a secretaria atualizar."
    if dados.genero is None:
        return "Seu gênero não está no cadastro da igreja. Peça para a secretaria atualizar."
    return None


@dataclass(frozen=True)
class Perfil:
    id: int
    membro_id: str
    igreja_id: str
    igreja_nome: str
    nome: str
    genero: Genero
    idade: int
    cidade: str = ""
    bairro: str = ""
    coordenadas: Optional[Tuple[float, float]] = None
    hobbies: Tuple[str, ...] = ()
    bio: str = ""
    tem_foto: bool = False
    idade_min: int = IDADE_MINIMA
    idade_max: int = 99
    raio_km: int = 30
    visivel: bool = True
    elegivel: bool = True
    codinome: str = ""
    simbolo: str = ""
    jornada: int = 0
    sequencia: int = 0
    ultimo_devocional: Optional[str] = None          # AAAA-MM-DD
    revelacoes: dict = field(default_factory=dict, compare=False)   # item → limite (None = só na mão)
    extras: dict = field(default_factory=dict, compare=False)

    @property
    def demo(self) -> bool:
        """Perfil de teste (modo demonstração): aparece para qualquer um, de qualquer cidade."""
        return self.membro_id.startswith("demo-")

    @property
    def completo(self) -> bool:
        """Só aparece para os outros quem escolheu os hobbies e mandou a foto (que fica escondida até liberar)."""
        return len(self.hobbies) >= HOBBIES_MINIMOS and self.tem_foto

    @property
    def nome_publico(self) -> str:
        return primeiro_nome(self.nome)

    def com(self, **mudancas) -> "Perfil":
        return replace(self, **mudancas)


def limpar_hobbies(escolhidos) -> Tuple[str, ...]:
    """Só os do catálogo, sem repetir, na ordem do catálogo."""
    validos = {h for h in (escolhidos or []) if h in HOBBIES}
    return tuple(h for h in HOBBIES if h in validos)[:HOBBIES_MAXIMOS]


def limpar_bio(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip()[:TAMANHO_BIO]


_CONTATO = re.compile(
    r"(\d[\s.\-()]*){8,}"                     # telefone
    r"|@[a-z0-9_.]{3,}"                       # @ de rede social
    r"|[\w.+-]+@[\w-]+\.[\w.]+"                # e-mail
    r"|https?://|www\.|\.com\b|\.com\.br\b"    # link
    r"|\b(insta|instagram|whats|whatsapp|zap|telegram|tiktok)\b", re.I)


def bio_tem_contato(texto: str) -> bool:
    """A conversa acontece aqui dentro, onde dá para denunciar. Contato externo na bio fica de fora."""
    return bool(_CONTATO.search(texto or ""))
