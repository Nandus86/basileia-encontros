"""A parte de jogo: jornada pessoal (devocional, testes), a afinidade da dupla e as revelações.

Dois placares diferentes:
- jornada (da pessoa): sobe com participação; deixa a análise mais profunda e libera mais sinais por dia;
- pontos da conexão (da dupla): sobem quando OS DOIS respondem a mesma coisa de forma parecida;
  liberam o que cada um escolheu revelar (idade com 300, bairro com 350, chat com 400…).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple

from encontros.dominio.perfil import sem_acento

# O "dia" do app é o de Brasília (o servidor roda em UTC). Fuso fixo: o Brasil não tem mais horário de verão.
FUSO = timezone(timedelta(hours=-3))


def hoje() -> date:
    return datetime.now(FUSO).date()


# ---------------- jornada pessoal ----------------

NIVEIS: Tuple[Tuple[str, int, int], ...] = (   # nome, pontos para chegar, sinais por dia
    ("Semente", 0, 3),
    ("Broto", 100, 3),
    ("Raiz", 250, 4),
    ("Árvore", 500, 4),
    ("Fruto", 900, 5),
)

PONTOS_DEVOCIONAL = 10
BONUS_POR_DIA_SEGUIDO = 2
BONUS_MAXIMO = 10
PONTOS_TESTE = 40
PONTOS_PERGUNTA_A_DOIS = 5


@dataclass(frozen=True)
class Nivel:
    nome: str
    minimo: int
    sinais_por_dia: int
    proximo: Optional[str]
    proximo_em: Optional[int]


def nivel_de(pontos: int) -> Nivel:
    atual = max((n for n in NIVEIS if pontos >= n[1]), key=lambda n: n[1])
    seguinte = next((n for n in NIVEIS if n[1] > pontos), None)
    return Nivel(atual[0], atual[1], atual[2], seguinte[0] if seguinte else None, seguinte[1] if seguinte else None)


def nova_sequencia(ultimo: Optional[str], hoje: date, atual: int) -> int:
    """Dias seguidos de devocional: ontem → +1; hoje de novo → igual; pulou um dia → recomeça."""
    if not ultimo:
        return 1
    dias = (hoje - date.fromisoformat(ultimo)).days
    return atual if dias == 0 else atual + 1 if dias == 1 else 1


def pontos_do_devocional(sequencia: int) -> int:
    return PONTOS_DEVOCIONAL + min(BONUS_MAXIMO, BONUS_POR_DIA_SEGUIDO * max(0, sequencia - 1))


def profundidade(testes: int, devocionais: int, perguntas: int) -> int:
    """Quanto a IA conhece a pessoa (%): os hobbies dão a base; testes e devocionais aprofundam."""
    return min(95, 40 + min(30, 10 * testes) + min(15, devocionais) + min(10, 2 * perguntas))


# ---------------- codinome (ninguém aparece pelo nome no começo) ----------------

CODINOMES = ("Cedro", "Oliveira", "Lírio", "Âncora", "Trigo", "Chama", "Orvalho", "Videira", "Estrela", "Monte",
             "Rio", "Lâmpada", "Pomba", "Rocha", "Farol", "Aurora", "Brisa", "Jardim", "Fonte", "Semente",
             "Romã", "Figueira", "Harpa", "Selo")
ADJETIVOS = ("Sereno", "Fiel", "Alegre", "Firme", "Manso", "Ousado", "Gentil", "Luminoso", "Paciente",
             "Constante", "Leal", "Vivo")
SIMBOLOS = ("🌿", "🕊️", "⚓", "🌾", "🔥", "💧", "🍇", "⭐", "⛰️", "🌊", "🪔", "🌸", "🌳", "🌙", "🍃", "☀️")


def sortear_codinome(sorte: Optional[random.Random] = None) -> Tuple[str, str]:
    sorte = sorte or random.SystemRandom()
    return f"{sorte.choice(CODINOMES)} {sorte.choice(ADJETIVOS)}", sorte.choice(SIMBOLOS)


# ---------------- revelações ----------------

ITENS: Tuple[Tuple[str, str], ...] = (
    ("sobre", "O que escrevi sobre mim"),
    ("nome", "Meu primeiro nome"),
    ("idade", "Minha idade"),
    ("bairro", "Meu bairro e cidade"),
    ("chat", "Conversar no chat"),
    ("foto", "Minha foto"),
    ("igreja", "Minha igreja"),
)
ROTULOS = dict(ITENS)
LIMIARES_PADRAO: Dict[str, Optional[int]] = {"sobre": 200, "nome": 250, "idade": 300, "bairro": 350, "chat": 400,
                                             "foto": 450, "igreja": 450}
LIMIARES_POSSIVEIS = tuple(range(150, 651, 50))     # None = só quando eu liberar na mão
SINTONIA_PARA_VER_NIVEL = 0.85


def limiares(config: Optional[Mapping[str, Optional[int]]]) -> Dict[str, Optional[int]]:
    """Os limites da pessoa, com os padrões no que ela não mexeu. Valor fora da lista volta ao padrão."""
    saida = dict(LIMIARES_PADRAO)
    for item, valor in (config or {}).items():
        if item in saida and (valor is None or valor in LIMIARES_POSSIVEIS):
            saida[item] = valor
    return saida


def revelou(item: str, limites: Mapping[str, Optional[int]], liberados: Iterable[str], pontos: int) -> bool:
    """Revelado para aquela conexão: liberado na mão, ou a dupla chegou no limite que a pessoa escolheu."""
    if item in set(liberados):
        return True
    limite = limites.get(item)
    return limite is not None and pontos >= limite


def chat_aberto(limites_a, liberados_a, limites_b, liberados_b, pontos: int) -> bool:
    """O chat precisa dos dois: vale o maior dos limites (ou os dois terem liberado na mão)."""
    return revelou("chat", limites_a, liberados_a, pontos) and revelou("chat", limites_b, liberados_b, pontos)


def chat_abre_em(limites_a, liberados_a, limites_b, liberados_b) -> Optional[int]:
    """Em quantos pontos o chat abre (None = depende de alguém liberar na mão)."""
    partes = []
    for limites, liberados in ((limites_a, liberados_a), (limites_b, liberados_b)):
        if "chat" in set(liberados):
            continue
        if limites.get("chat") is None:
            return None
        partes.append(limites["chat"])
    return max(partes) if partes else 0


# ---------------- afinidade da dupla ----------------

PONTOS_INICIAIS = {"alta": 200, "media": 150, "baixa": 100}
SINTONIA_INICIAL = {"alta": 0.9, "media": 0.75, "baixa": 0.5}

# como o JEV compara duas respostas abertas → (pontos, sintonia)
NOTAS_DA_COMPARACAO: Dict[str, Tuple[int, float]] = {
    "muito_parecidas": (30, 1.0),
    "parecidas": (20, 0.85),
    "complementares": (15, 0.7),
    "diferentes": (5, 0.35),
}
PONTOS_TESTE_DA_DUPLA = 50
FATOR_DEVOCIONAL = 0.5        # devocional em comum vale metade de uma pergunta a dois


def semelhanca_das_escolhas(a: Sequence[int], b: Sequence[int], opcoes: int = 4) -> float:
    """Testes de múltipla escolha: as opções vão de um extremo ao outro, então 1 e 2 estão mais perto que 1 e 4."""
    pares = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pares:
        return 0.0
    return sum(1 - abs(x - y) / (opcoes - 1) for x, y in pares) / len(pares)


def pontos_do_teste(semelhanca: float) -> int:
    return round(PONTOS_TESTE_DA_DUPLA * semelhanca)


_PALAVRA = re.compile(r"[a-z]{4,}")


def comparacao_por_palavras(a: str, b: str) -> str:
    """Reserva sem IA: quantas palavras com sentido as duas respostas dividem."""
    pa, pb = set(_PALAVRA.findall(sem_acento(a))), set(_PALAVRA.findall(sem_acento(b)))
    if not pa or not pb:
        return "diferentes"
    j = len(pa & pb) / len(pa | pb)
    return "parecidas" if j >= 0.3 else "complementares" if j >= 0.12 else "diferentes"


TEMAS: Dict[str, str] = {
    "fe_e_confianca": "Fé, confiança em Deus nas incertezas",
    "oracao_e_intimidade": "Oração, intimidade com Deus, tempo a sós",
    "familia": "Família, pais, filhos, lar",
    "perdao": "Perdão, reconciliação, graça",
    "proposito": "Propósito, chamado, vocação",
    "servico": "Servir, ministério, ajudar o próximo",
    "gratidao_e_alegria": "Gratidão, alegria, louvor",
    "ansiedade_e_paz": "Ansiedade, medo, descanso e paz",
    "relacionamentos": "Amizade, namoro, comunhão",
    "sabedoria_e_decisoes": "Sabedoria, decisões, conselho",
}

TEMAS_CURTOS = {"fe_e_confianca": "confiança em Deus", "oracao_e_intimidade": "oração", "familia": "família",
                "perdao": "perdão", "proposito": "propósito", "servico": "servir", "gratidao_e_alegria": "gratidão",
                "ansiedade_e_paz": "paz nas lutas", "relacionamentos": "relacionamentos",
                "sabedoria_e_decisoes": "sabedoria nas decisões"}

_PALAVRAS_DOS_TEMAS = {
    "fe_e_confianca": ("confi", "fe ", "fé", "duvid", "promess"), "oracao_e_intimidade": ("ora", "intimid", "silenc"),
    "familia": ("famil", "pai", "mae", "filh", "casa"), "perdao": ("perdo", "perdã", "magoa", "reconcil", "graca"),
    "proposito": ("propos", "chamad", "vocac"), "servico": ("serv", "ministe", "ajud", "proxim"),
    "gratidao_e_alegria": ("grat", "alegr", "louv"), "ansiedade_e_paz": ("ansie", "medo", "paz", "descans"),
    "relacionamentos": ("amig", "namor", "comunh", "relacion"), "sabedoria_e_decisoes": ("sabed", "decis", "consel"),
}


def temas_por_palavras(texto: str) -> Tuple[str, ...]:
    t = sem_acento(texto)
    achados = [tema for tema, raizes in _PALAVRAS_DOS_TEMAS.items() if any(sem_acento(r) in t for r in raizes)]
    return tuple(achados[:2])


def semelhanca_dos_temas(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def itens_validos(itens: Iterable[str]) -> FrozenSet[str]:
    return frozenset(i for i in itens if i in ROTULOS)
