"""Julgadores (mesmo desenho do Motor de Cuidado): o JEV da OpenRouter, rápido e tipado, e uma reserva
por LLM pedindo JSON, para quando o JEV falhar (o endpoint de decisões ainda é alpha)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Mapping, Optional

import httpx

from encontros.aplicacao.portas import Julgamento, Pergunta

logger = logging.getLogger(__name__)

BASE = "https://openrouter.ai/api"


class ErroOpenRouter(RuntimeError):
    pass


class ClienteOpenRouter:
    def __init__(self, chave: str, timeout: float = 30.0):
        if not chave:
            raise ErroOpenRouter("chave da OpenRouter não configurada (ENCONTROS_OPENROUTER_API_KEY)")
        self._cabecalhos = {"Authorization": f"Bearer {chave}", "X-Title": "Basileia - Encontros"}
        self._http = httpx.AsyncClient(base_url=BASE, timeout=timeout, headers=self._cabecalhos)

    async def conversar(self, modelo: str, mensagens: List[Mapping[str, str]], provedores: Optional[List[str]] = None,
                        max_tokens: int = 200) -> str:
        corpo: Dict[str, Any] = {"model": modelo, "messages": list(mensagens), "temperature": 0,
                                 "max_tokens": max_tokens, "reasoning": {"enabled": False},
                                 "response_format": {"type": "json_object"}}
        if provedores:
            corpo["provider"] = {"only": provedores}
        r = await self._http.post("/v1/chat/completions", json=corpo)
        dados = r.json() if r.content else {}
        try:
            texto = dados["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ErroOpenRouter(f"resposta inesperada ({r.status_code}): {str(dados)[:200]}")
        if not texto.strip():
            raise ErroOpenRouter("resposta vazia")
        return texto.strip()

    async def decidir(self, estado: str, perguntas: Mapping[str, Any], modelo: str) -> Dict[str, Any]:
        r = await self._http.post("/alpha/decisions", json={"model": modelo, "state": estado, "questions": dict(perguntas)},
                                  timeout=20.0)
        if r.status_code != 200:
            raise ErroOpenRouter(f"decisões indisponíveis ({r.status_code}): {r.text[:200]}")
        dados = r.json()
        return dados.get("answers", dados)

    async def fechar(self) -> None:
        await self._http.aclose()


def _validar(respostas: Mapping[str, Any], perguntas: Mapping[str, Pergunta]) -> Dict[str, str]:
    saida = {}
    for nome, pergunta in perguntas.items():
        escolha = str(respostas.get(nome) or "").strip()
        if escolha not in pergunta.opcoes:
            raise ValueError(f"resposta fora das opções para '{nome}': {escolha!r}")
        saida[nome] = escolha
    return saida


class JulgadorJev:
    def __init__(self, cliente: ClienteOpenRouter, modelo: str = "~typesafe/jev-latest"):
        self._cliente = cliente
        self._modelo = modelo

    async def julgar(self, estado: str, perguntas: Mapping[str, Pergunta]) -> Julgamento:
        questoes = {nome: {"type": "choice", "instructions": p.instrucao, "criteria": dict(p.opcoes)}
                    for nome, p in perguntas.items()}
        respostas = await self._cliente.decidir(estado, questoes, self._modelo)
        escolhas = {n: (v.get("choice") if isinstance(v, dict) else v) for n, v in respostas.items()}
        return Julgamento(_validar(escolhas, perguntas), "jev")


class JulgadorLLM:
    """Reserva: o mesmo julgamento por um modelo de conversa, pedindo JSON."""

    def __init__(self, cliente: ClienteOpenRouter, modelo: str, provedores: Optional[List[str]] = None):
        self._cliente = cliente
        self._modelo = modelo
        self._provedores = provedores

    async def julgar(self, estado: str, perguntas: Mapping[str, Pergunta]) -> Julgamento:
        descricao = "\n".join(
            f'- "{nome}": {p.instrucao} Opções: ' + "; ".join(f'"{k}" = {v}' for k, v in p.opcoes.items())
            for nome, p in perguntas.items())
        sistema = ("Você avalia perfis de um app de relacionamento cristão e responde perguntas fechadas. "
                   "Responda APENAS com um objeto JSON com uma chave por pergunta e, como valor, exatamente uma das "
                   f"opções permitidas.\n\nPerguntas:\n{descricao}")
        texto = await self._cliente.conversar(self._modelo, [{"role": "system", "content": sistema},
                                                             {"role": "user", "content": estado}],
                                              provedores=self._provedores)
        achado = re.search(r"\{.*\}", texto, re.S)
        return Julgamento(_validar(json.loads(achado.group(0) if achado else texto), perguntas), "llm")


class JulgadorComReserva:
    def __init__(self, principal, reserva):
        self._principal = principal
        self._reserva = reserva

    async def julgar(self, estado: str, perguntas: Mapping[str, Pergunta]) -> Julgamento:
        try:
            return await self._principal.julgar(estado, perguntas)
        except Exception as erro:
            logger.warning("[encontros] JEV falhou (%s) — usando a reserva", str(erro)[:150])
            return await self._reserva.julgar(estado, perguntas)
