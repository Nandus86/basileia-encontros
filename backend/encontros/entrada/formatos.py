"""Como as coisas saem da API. Regra de ouro: da outra pessoa só sai o que ela revelou (codinome e interesses sempre)."""
from __future__ import annotations

from typing import Mapping, Optional

from encontros.aplicacao.conexoes import PerguntaDaVez, Sinal, VisaoDaConexao
from encontros.aplicacao.jornada import ResumoDaJornada
from encontros.aplicacao.portas import Conteudo, EventoDaDupla, Mensagem
from encontros.dominio.afinidade import em_comum
from encontros.dominio.jornada import ITENS, LIMIARES_POSSIVEIS, limiares
from encontros.dominio.perfil import Perfil

NADA_REVELADO = {item: False for item, _ in ITENS}


def meu_perfil(p: Perfil) -> dict:
    meus = limiares(p.revelacoes)
    return {"id": p.id, "nome": p.nome, "nome_publico": p.nome_publico, "idade": p.idade, "genero": p.genero.value,
            "cidade": p.cidade, "bairro": p.bairro, "igreja": p.igreja_nome, "hobbies": list(p.hobbies),
            "bio": p.bio, "tem_foto": p.tem_foto, "idade_min": p.idade_min, "idade_max": p.idade_max,
            "raio_km": p.raio_km, "visivel": p.visivel, "completo": p.completo,
            "tem_localizacao": p.coordenadas is not None, "local_do_app": bool(p.extras.get("local_do_app")),
            "codinome": p.codinome, "simbolo": p.simbolo, "jornada": p.jornada,
            "revelacoes": [{"item": item, "rotulo": rotulo, "limite": meus[item]} for item, rotulo in ITENS],
            "limites_possiveis": list(LIMIARES_POSSIVEIS)}


def publico(p: Perfil, eu: Perfil, revelado: Mapping[str, bool] = NADA_REVELADO) -> dict:
    """A outra pessoa como eu a vejo: o codinome e os interesses; o resto, se ela revelou."""
    local = ", ".join(x for x in (p.bairro, p.cidade) if x) if revelado.get("bairro") else None
    return {"id": p.id, "codinome": p.codinome or "Anônimo", "simbolo": p.simbolo or "✦",
            "hobbies": list(p.hobbies), "em_comum": list(em_comum(eu, p)),
            "nome": p.nome_publico if revelado.get("nome") else None,
            "idade": p.idade if revelado.get("idade") else None, "local": local,
            "sobre": (p.bio or None) if revelado.get("sobre") else None,
            "igreja": p.igreja_nome if revelado.get("igreja") else None,
            "foto": bool(revelado.get("foto") and p.tem_foto)}


def sinal(s: Sinal, eu: Perfil) -> dict:
    return {**publico(s.pessoa, eu), "motivos": list(s.motivos),
            "afinidade": s.afinidade.nivel.value if s.afinidade else None}


def mensagem(m: Mensagem, eu_id: int) -> dict:
    return {"id": m.id, "texto": m.texto, "minha": m.autor_id == eu_id, "criado_em": m.criado_em}


def evento(e: EventoDaDupla) -> dict:
    return {"tipo": e.tipo, "titulo": e.titulo, "pontos": e.pontos, "sintonia": round(e.sintonia * 100),
            "criado_em": e.criado_em}


def pergunta(vez: PerguntaDaVez) -> dict:
    anterior = ({"texto": vez.anterior.conteudo.dados.get("texto"), "minha": vez.anterior.minha.dados.get("texto"),
                 "dela": vez.anterior.dela.dados.get("texto")} if vez.anterior else None)
    atual = None
    if vez.conteudo:
        atual = {"id": vez.conteudo.id, "texto": vez.conteudo.dados.get("texto"),
                 "minha": vez.minha.dados.get("texto") if vez.minha else None,
                 "dela": vez.dela.dados.get("texto") if vez.dela else None}
    return {"atual": atual, "volta_amanha": vez.volta_amanha, "anterior": anterior}


def resumo_da_conexao(v: VisaoDaConexao, eu: Perfil, extra: Mapping) -> dict:
    sintonia = v.conexao.sintonia
    return {"id": v.conexao.id, "criado_em": v.conexao.criado_em, "outra": publico(v.outra, eu, v.dela),
            "pontos": v.conexao.pontos, "sintonia": round(sintonia * 100) if sintonia is not None else None,
            "chat_aberto": v.chat_aberto, "chat_abre_em": v.chat_abre_em, "nivel_dela": v.nivel_dela,
            "proxima_descoberta": ({"rotulo": v.proxima_descoberta[0], "pontos": v.proxima_descoberta[1]}
                                   if v.proxima_descoberta else None), **extra}


def minhas_revelacoes(v: VisaoDaConexao) -> list:
    return [{"item": r.item, "rotulo": r.rotulo, "limite": r.limite, "revelado": r.revelado, "na_mao": r.na_mao}
            for r in v.minhas]


def jornada(r: ResumoDaJornada) -> dict:
    n = r.nivel
    return {"pontos": r.pontos, "nivel": n.nome, "nivel_desde": n.minimo, "proximo_nivel": n.proximo,
            "proximo_em": n.proximo_em, "sinais_por_dia": n.sinais_por_dia, "sequencia": r.sequencia,
            "profundidade": r.profundidade, "devocional_hoje": r.devocional_hoje, "testes_feitos": r.testes_feitos}


def devocional(c: Conteudo, minha: Optional[str]) -> dict:
    return {"id": c.id, "dia": c.dia, **{k: c.dados.get(k) for k in ("titulo", "referencia", "reflexao", "pergunta")},
            "minha": minha}


def teste(c: Conteudo, feito: bool, com_questoes: bool = False) -> dict:
    saida = {"id": c.id, "titulo": c.dados.get("titulo"), "tema": c.dados.get("tema"),
             "questoes": len(c.dados.get("questoes") or []), "feito": feito}
    if com_questoes:
        saida["lista"] = c.dados.get("questoes") or []
    return saida


def conteudo(c: Conteudo) -> dict:
    return {"id": c.id, "tipo": c.tipo, "status": c.status, "origem": c.origem, "dados": dict(c.dados), "dia": c.dia,
            "criado_em": c.criado_em}
