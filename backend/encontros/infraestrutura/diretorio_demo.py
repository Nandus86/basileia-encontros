"""Modo de teste: perfis prontos que "jogam" sozinhos, para testar o app sem precisar de gente de verdade.

Liga com ENCONTROS_MODO_DEMO=true. Se o Mongo do CRM também estiver configurado, os dois valem juntos:
as contas de teste entram e os CPFs reais também (cada um com o seu cadastro).

O que os perfis de teste (bots) fazem:
- devolvem o sinal na hora;
- respondem a pergunta a dois, o devocional e os testes logo depois de você;
- respondem no chat;
- quem entra ganha 3 conexões já adiantadas (150, 290 e 390 pontos) para testar as revelações.
"""
from __future__ import annotations

import logging
import zlib
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from encontros.aplicacao.portas import Candidata, Conexao, Conteudo, Diretorio, Repositorio, Resposta
from encontros.dominio.jornada import temas_por_palavras
from encontros.dominio.perfil import DadosDoCrm, Genero, Perfil, TipoDePessoa
from encontros.infraestrutura.conteudo_semente import (DEVOCIONAIS, ESCOLHAS_DOS_BOTS, MENSAGENS_DOS_BOTS,
                                                       PENDENTES_DE_EXEMPLO, PERGUNTAS, RESPOSTAS_DOS_BOTS, TESTES)
from encontros.infraestrutura.fotos import Fotos

logger = logging.getLogger(__name__)

IGREJA_ID = "demo-igreja"
IGREJA_NOME = "Igreja Demonstração"

FLORIANO = (-6.7669, -43.0225)
BARAO = (-6.7445, -43.0261)         # do outro lado do rio, ~3 km
AMARANTE = (-6.2425, -42.8464)      # ~60 km
TERESINA = (-5.0920, -42.8038)      # ~190 km


@dataclass(frozen=True)
class PessoaDemo:
    cpf: str
    nome: str
    genero: Optional[Genero]
    idade: int
    cidade: str
    bairro: str
    coordenadas: Optional[Tuple[float, float]]
    estado_civil: str = "solteiro"
    tipo: TipoDePessoa = TipoDePessoa.MEMBRO
    hobbies: Tuple[str, ...] = ()
    bio: str = ""
    cor: Tuple[int, int, int] = (91, 33, 182)
    jeito: str = "contemplativo"         # como o bot responde (ver conteudo_semente.JEITOS)
    revelacoes: Tuple[Tuple[str, Optional[int]], ...] = ()
    entrada: str = ""                    # contas para entrar (o resto são bots)


LUCAS, ANA = "11144477735", "22255588846"

PESSOAS = (
    # contas para entrar (o perfil é completado no app)
    PessoaDemo(LUCAS, "Lucas Andrade", Genero.MASCULINO, 27, "Floriano", "Centro", FLORIANO,
               entrada="Lucas, 27 — solteiro, perfil para completar"),
    PessoaDemo(ANA, "Ana Beatriz Souza", Genero.FEMININO, 25, "Floriano", "Irapuá", FLORIANO,
               entrada="Ana, 25 — solteira, perfil para completar"),
    PessoaDemo("33366699957", "Pedro Lima", Genero.MASCULINO, 17, "Floriano", "Centro", FLORIANO,
               entrada="Pedro, 17 — menor de idade (não entra)"),
    PessoaDemo("44477700083", "Marcos Ribeiro", Genero.MASCULINO, 34, "Floriano", "Centro", FLORIANO,
               estado_civil="casado", entrada="Marcos, 34 — casado (não entra)"),
    PessoaDemo("55588811194", "Júlia Castro", Genero.FEMININO, 22, "Floriano", "Centro", FLORIANO,
               tipo=TipoDePessoa.VISITANTE, entrada="Júlia, 22 — visitante (não entra)"),
    # bots: elas…
    PessoaDemo("12345678909", "Débora Martins", Genero.FEMININO, 24, "Floriano", "Centro", FLORIANO,
               hobbies=("Louvor e música", "Tocar instrumento", "Café", "Leitura bíblica", "Fotografia"),
               bio="Toco violão no ministério de louvor. Amo um café depois do culto de domingo.",
               cor=(124, 58, 237), jeito="alegre", revelacoes=(("nome", 150), ("idade", 200))),
    PessoaDemo("98765432100", "Raquel Nunes", Genero.FEMININO, 28, "Floriano", "Sambaíba", FLORIANO,
               hobbies=("Corrida", "Academia", "Trilhas e natureza", "Viagens", "Café"),
               bio="Corro aos sábados cedo e adoro uma trilha. Sirvo na recepção.", cor=(190, 24, 93), jeito="servidor"),
    PessoaDemo("13579246828", "Sara Oliveira", Genero.FEMININO, 26, "Barão de Grajaú", "Centro", BARAO,
               hobbies=("Missões", "Voluntariado", "Ministério infantil", "Cozinhar", "Leitura bíblica"),
               bio="Sirvo no ministério infantil e sonho em fazer missões. Faço o melhor bolo de milho da cidade.",
               cor=(14, 116, 144), jeito="servidor", revelacoes=(("chat", 300),)),
    PessoaDemo("24681357928", "Lídia Carvalho", Genero.FEMININO, 23, "Floriano", "Manguinha", FLORIANO,
               hobbies=("Games", "Tecnologia", "Cinema e séries", "Idiomas", "Leitura"),
               bio="Desenvolvedora, gamer e fã de séries. Estudando coreano.", cor=(67, 56, 202)),
    PessoaDemo("11223344517", "Priscila Moura", Genero.FEMININO, 29, "Teresina", "Jóquei", TERESINA,
               hobbies=("Louvor e música", "Café", "Viagens", "Leitura"), bio="Ministra de louvor em Teresina.",
               cor=(161, 98, 7), jeito="alegre"),
    PessoaDemo("66778899100", "Ester Lima", Genero.FEMININO, 31, "Floriano", "Centro", FLORIANO,
               hobbies=("Estudos teológicos", "Leitura bíblica", "Café", "Jardinagem"),
               bio="Professora da escola bíblica. Gosto de conversas profundas e de plantas.", cor=(5, 150, 105)),
    # …e eles
    PessoaDemo("55667788950", "Gabriel Rocha", Genero.MASCULINO, 27, "Floriano", "Centro", FLORIANO,
               hobbies=("Louvor e música", "Tocar instrumento", "Futebol", "Café"),
               bio="Baterista no louvor, zagueiro no futebol de quinta. Café sem açúcar.",
               cor=(30, 64, 175), jeito="alegre", revelacoes=(("nome", 150),)),
    PessoaDemo("99887766593", "Samuel Freitas", Genero.MASCULINO, 29, "Floriano", "Tiberão", FLORIANO,
               hobbies=("Leitura", "Estudos teológicos", "Café", "Idiomas"),
               bio="Professor da EBD. Sempre com um livro na mochila.", cor=(4, 120, 87)),
    PessoaDemo("44332211049", "Davi Pereira", Genero.MASCULINO, 26, "Barão de Grajaú", "Centro", BARAO,
               hobbies=("Corrida", "Ciclismo", "Trilhas e natureza", "Fotografia", "Viagens"),
               bio="Pedalo nos fins de semana e fotografo tudo pelo caminho.", cor=(194, 65, 12), jeito="servidor"),
    PessoaDemo("10203040570", "Tiago Mendes", Genero.MASCULINO, 31, "Amarante", "Centro", AMARANTE,
               hobbies=("Louvor e música", "Cozinhar", "Pets", "Voluntariado"), bio="Líder de célula em Amarante.",
               cor=(87, 83, 78), jeito="servidor", revelacoes=(("chat", 300),)),
    PessoaDemo("50403020107", "Mateus Araújo", Genero.MASCULINO, 24, "Floriano", "Centro", FLORIANO,
               hobbies=("Games", "Tecnologia", "Futebol", "Cinema e séries"), bio="Técnico de som da igreja.",
               cor=(109, 40, 217), jeito="alegre"),
)

PONTOS_DAS_CONEXOES_PRONTAS = (390, 290, 150)


def _membro_id(p: PessoaDemo) -> str:
    return f"demo-{p.cpf}"


BOTS = {_membro_id(p): p for p in PESSOAS if not p.entrada}


def _dados(p: PessoaDemo) -> DadosDoCrm:
    return DadosDoCrm(membro_id=_membro_id(p), igreja_id=IGREJA_ID, igreja_nome=IGREJA_NOME, nome=p.nome,
                      tipo=p.tipo, genero=p.genero, idade=p.idade, estado_civil=p.estado_civil, cidade=p.cidade,
                      bairro=p.bairro, coordenadas=p.coordenadas)


def contas_de_teste() -> list:
    return [{"cpf": p.cpf, "descricao": p.entrada} for p in PESSOAS if p.entrada]


class DiretorioDemo:
    async def candidatas(self, variantes_do_cpf: Sequence[str]) -> Sequence[Candidata]:
        return [Candidata(membro_id=_membro_id(p), igreja_id=IGREJA_ID, igreja_nome=IGREJA_NOME, nome=p.nome)
                for p in PESSOAS if p.cpf in set(variantes_do_cpf)]

    async def dados(self, igreja_id: str, membro_id: str) -> Optional[DadosDoCrm]:
        return next((_dados(p) for p in PESSOAS if _membro_id(p) == membro_id and igreja_id == IGREJA_ID), None)

    async def fechar(self) -> None:
        pass


class DiretorioCombinado:
    """Contas de teste + CRM de verdade, ao mesmo tempo."""

    def __init__(self, demo: DiretorioDemo, real: Diretorio):
        self._demo = demo
        self._real = real

    async def candidatas(self, variantes_do_cpf: Sequence[str]) -> Sequence[Candidata]:
        return [*await self._demo.candidatas(variantes_do_cpf), *await self._real.candidatas(variantes_do_cpf)]

    async def dados(self, igreja_id: str, membro_id: str) -> Optional[DadosDoCrm]:
        if igreja_id == IGREJA_ID:
            return await self._demo.dados(igreja_id, membro_id)
        return await self._real.dados(igreja_id, membro_id)


async def semear_conteudo(repo: Repositorio, aprovado: bool) -> None:
    """O conteúdo inicial, uma vez só (quando não há nenhum)."""
    if await repo.conteudos():
        return
    status = "aprovado" if aprovado else "pendente"
    for d in DEVOCIONAIS:
        await repo.salvar_conteudo("devocional", d, status, "semente")
    for texto in PERGUNTAS:
        await repo.salvar_conteudo("pergunta", {"texto": texto}, status, "semente")
    for t in TESTES:
        await repo.salvar_conteudo("teste", t, status, "semente")
    if aprovado:
        for tipo, dados in PENDENTES_DE_EXEMPLO:
            await repo.salvar_conteudo(tipo, dados, "pendente", "ia")
    logger.info("[encontros] conteúdo inicial criado (%s)", status)


async def semear_pessoas(repo: Repositorio, fotos: Fotos) -> List[int]:
    """Os perfis de teste: cria ou atualiza (pode rodar a cada subida). Devolve os ids dos bots."""
    bots = []
    for p in PESSOAS:
        if p.genero is None or p.estado_civil != "solteiro" or p.tipo != TipoDePessoa.MEMBRO or p.idade < 18:
            continue
        perfil = await repo.salvar_do_crm(_dados(p))
        if p.hobbies and not perfil.tem_foto:
            await repo.atualizar_perfil(perfil.id, hobbies=p.hobbies, bio=p.bio, revelacoes=dict(p.revelacoes),
                                        foto=fotos.gerar_de_exemplo(p.nome[0], p.cor))
        if not p.entrada:
            bots.append(perfil.id)
    return bots


class BotsDeTeste:
    """Faz os perfis de teste participarem. `conexoes` é ligado depois (os casos de uso dependem dos bots)."""

    def __init__(self, repo: Repositorio, ids: Sequence[int]):
        self._repo = repo
        self._ids = list(ids)
        self.conexoes = None

    @staticmethod
    def e_bot(pessoa: Perfil) -> bool:
        return pessoa.membro_id in BOTS

    async def ao_entrar(self, pessoa: Perfil) -> None:
        """Quem entra pela primeira vez ganha conexões adiantadas para testar as revelações."""
        if self.e_bot(pessoa) or await self._repo.conexoes_de(pessoa.id):
            return
        perfis = await self._repo.perfis(self._ids)
        candidatos = [perfis[i] for i in self._ids if i in perfis and perfis[i].genero == pessoa.genero.oposto
                      and perfis[i].completo and perfis[i].elegivel]
        for bot, pontos in zip(candidatos, PONTOS_DAS_CONEXOES_PRONTAS):
            await self._repo.reagir(bot.id, pessoa.id, True)
            conexao = await self._repo.reagir(pessoa.id, bot.id, True)
            if conexao:
                await self.conexoes.iniciar(conexao, pessoa, bot, pontos=pontos)

    async def responder_testes(self) -> None:
        """Os bots fazem os testes aprovados (assim a análise mais funda já tem com o que comparar)."""
        perfis = await self._repo.perfis(self._ids)
        for teste in await self._repo.conteudos("teste", "aprovado"):
            for bot in perfis.values():
                await self.responder_se_preciso(bot, teste)

    async def ao_enviar_sinal(self, de: Perfil, para: Perfil) -> None:
        if self.e_bot(para):
            await self._repo.reagir(para.id, de.id, True)

    async def responder_se_preciso(self, bot: Perfil, conteudo: Conteudo) -> None:
        if not self.e_bot(bot) or await self._repo.resposta(bot.id, conteudo.id):
            return
        jeito = BOTS[bot.membro_id].jeito
        if conteudo.tipo == "teste":
            base = ESCOLHAS_DOS_BOTS[jeito]
            escolhas = [min(3, base + (zlib.crc32(f"{bot.id}-{conteudo.id}-{i}".encode()) % 3 == 0))
                        for i in range(len(conteudo.dados.get("questoes") or []))]
            await self._repo.salvar_resposta(Resposta(bot.id, conteudo.id, {"escolhas": escolhas}))
            return
        opcoes = RESPOSTAS_DOS_BOTS[jeito]
        texto = opcoes[zlib.crc32(f"{conteudo.id}".encode()) % len(opcoes)]
        await self._repo.salvar_resposta(Resposta(bot.id, conteudo.id, {"texto": texto}, temas_por_palavras(texto)))

    async def ao_receber_mensagem(self, conexao: Conexao, bot: Perfil) -> None:
        if not self.e_bot(bot):
            return
        minhas = [m for m in await self._repo.mensagens(conexao.id) if m.autor_id == bot.id]
        await self._repo.enviar(conexao.id, bot.id, MENSAGENS_DOS_BOTS[len(minhas) % len(MENSAGENS_DOS_BOTS)])
