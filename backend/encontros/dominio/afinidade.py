"""Quem pode ver quem (regras duras) e o que conta como "ter as mesmas características" (afinidade)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from encontros.dominio.perfil import Perfil, distancia_km, sem_acento


class Nivel(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class Proximidade(str, Enum):
    PERTO = "perto"
    RAZOAVEL = "razoavel"
    LONGE = "longe"


ORDEM_DO_NIVEL = {Nivel.ALTA: 0, Nivel.MEDIA: 1, Nivel.BAIXA: 2}


@dataclass(frozen=True)
class Afinidade:
    nivel: Nivel
    proximidade: Proximidade
    apresentar: bool
    em_comum: Tuple[str, ...] = ()
    origem: str = "regras"          # jev, llm ou regras

    @property
    def compativel(self) -> bool:
        """Só vira cartão (e só pode receber curtida) quem tem afinidade de verdade e mora perto o bastante."""
        return self.apresentar and self.nivel != Nivel.BAIXA and self.proximidade != Proximidade.LONGE


def par(a_id: int, b_id: int) -> Tuple[int, int]:
    """A afinidade é a mesma nos dois sentidos: guardada uma vez só, com o menor id primeiro."""
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def em_comum(a: Perfil, b: Perfil) -> Tuple[str, ...]:
    return tuple(h for h in a.hobbies if h in set(b.hobbies))


def distancia_entre(a: Perfil, b: Perfil) -> Optional[float]:
    if a.coordenadas and b.coordenadas:
        return distancia_km(a.coordenadas, b.coordenadas)
    return None


def mesma_cidade(a: Perfil, b: Perfil) -> bool:
    return bool(a.cidade) and sem_acento(a.cidade) == sem_acento(b.cidade)


def podem_se_ver(a: Perfil, b: Perfil) -> bool:
    """Regras duras, nos dois sentidos, antes de gastar IA: gêneros opostos, idade que cada um aceita e
    distância dentro do raio dos dois (sem localização de algum deles, só a mesma cidade)."""
    if a.id == b.id or not (a.elegivel and b.elegivel and a.visivel and b.visivel and a.completo and b.completo):
        return False
    if b.genero != a.genero.oposto:
        return False
    if not (a.idade_min <= b.idade <= a.idade_max and b.idade_min <= a.idade <= b.idade_max):
        return False
    km = distancia_entre(a, b)
    if km is None:
        return mesma_cidade(a, b)
    return km <= min(a.raio_km, b.raio_km)


def afinidade_por_regras(a: Perfil, b: Perfil) -> Afinidade:
    """Reserva quando o JEV e o modelo de reserva estão fora: só hobbies iguais contam."""
    comuns = em_comum(a, b)
    uniao = len(set(a.hobbies) | set(b.hobbies)) or 1
    if len(comuns) >= 3 or len(comuns) / uniao >= 0.5:
        nivel = Nivel.ALTA
    elif len(comuns) == 2:
        nivel = Nivel.MEDIA
    else:
        nivel = Nivel.BAIXA
    km = distancia_entre(a, b)
    if km is None:
        proximidade = Proximidade.PERTO if mesma_cidade(a, b) else Proximidade.LONGE
    elif km <= 15:
        proximidade = Proximidade.PERTO
    elif km <= min(a.raio_km, b.raio_km):
        proximidade = Proximidade.RAZOAVEL
    else:
        proximidade = Proximidade.LONGE
    return Afinidade(nivel=nivel, proximidade=proximidade, apresentar=nivel != Nivel.BAIXA, em_comum=comuns)


def assinatura(a: Perfil, b: Perfil) -> str:
    """Muda quando muda algo que o julgamento considerou: aí a afinidade guardada vale de novo ser julgada."""
    def parte(p: Perfil):
        coordenadas = [round(c, 2) for c in p.coordenadas] if p.coordenadas else None
        return [p.id, list(p.hobbies), p.bio, p.cidade, coordenadas, p.raio_km, p.idade]
    primeiro, segundo = (a, b) if a.id < b.id else (b, a)
    texto = json.dumps([parte(primeiro), parte(segundo)], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(texto.encode()).hexdigest()[:20]


def descrever_para_o_julgador(a: Perfil, b: Perfil) -> str:
    """O estado que o JEV lê: sem nomes, sem igreja, só o que importa para afinidade e localização."""
    def pessoa(rotulo: str, p: Perfil) -> str:
        onde = ", ".join(x for x in (p.bairro, p.cidade) if x) or "local não informado"
        sobre = p.bio or "(não escreveu)"
        return (f"{rotulo}: {p.idade} anos, mora em {onde}. Aceita conhecer pessoas a até {p.raio_km} km.\n"
                f"  Hobbies: {', '.join(p.hobbies) or '(nenhum)'}\n  Sobre: {sobre}")
    km = distancia_entre(a, b)
    if km is not None:
        distancia = f"Distância entre as duas: cerca de {round(km)} km."
    else:
        distancia = "Distância exata desconhecida; " + ("moram na mesma cidade." if mesma_cidade(a, b) else "cidades diferentes.")
    comuns = em_comum(a, b)
    return "\n".join([
        "Duas pessoas cristãs, solteiras e maiores de idade, membros de igreja, num app de relacionamento.",
        pessoa("Pessoa A", a), pessoa("Pessoa B", b), distancia,
        f"Hobbies exatamente iguais: {', '.join(comuns) if comuns else 'nenhum'}.",
    ])
