"""Pontos da dupla: quando OS DOIS responderam o mesmo conteúdo, compara e soma (uma vez por conteúdo)."""
from __future__ import annotations

from typing import Optional

from encontros.aplicacao.comparador import Comparador
from encontros.aplicacao.portas import Conexao, Conteudo, EventoDaDupla, Repositorio
from encontros.dominio.jornada import (FATOR_DEVOCIONAL, NOTAS_DA_COMPARACAO, pontos_do_teste,
                                       semelhanca_das_escolhas)

TITULOS = {"pergunta": "Pergunta a dois", "devocional": "Devocional em comum", "teste": "Teste em comum"}


def referencia(conteudo: Conteudo) -> str:
    return f"conteudo:{conteudo.id}"


class Pontuacao:
    def __init__(self, repositorio: Repositorio, comparador: Comparador):
        self._repo = repositorio
        self._comparador = comparador

    async def pontuar(self, conexao: Conexao, conteudo: Conteudo) -> Optional[EventoDaDupla]:
        if conexao.desfeita or await self._repo.tem_evento(conexao.id, referencia(conteudo)):
            return None
        respostas = {r.pessoa_id: r for r in await self._repo.respostas([conexao.a_id, conexao.b_id], [conteudo.id])}
        if len(respostas) < 2:
            return None
        a, b = respostas[conexao.a_id].dados, respostas[conexao.b_id].dados
        if conteudo.tipo == "teste":
            semelhanca = semelhanca_das_escolhas(a.get("escolhas") or [], b.get("escolhas") or [])
            pontos = pontos_do_teste(semelhanca)
        else:
            pergunta = conteudo.dados.get("texto") or conteudo.dados.get("pergunta") or ""
            nota = await self._comparador.comparar(pergunta, a.get("texto", ""), b.get("texto", ""))
            pontos, semelhanca = NOTAS_DA_COMPARACAO[nota]
            if conteudo.tipo == "devocional":
                pontos = round(pontos * FATOR_DEVOCIONAL)
        evento = EventoDaDupla(tipo=conteudo.tipo, titulo=f"{TITULOS[conteudo.tipo]}: {conteudo.titulo}"[:200],
                               pontos=pontos, sintonia=round(semelhanca, 3))
        return evento if await self._repo.registrar_evento(conexao.id, referencia(conteudo), evento) else None
