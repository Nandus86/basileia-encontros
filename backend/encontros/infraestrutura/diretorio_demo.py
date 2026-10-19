"""Modo demonstração: um CRM de mentira (sem Mongo) e perfis prontos, para ver o app funcionando no computador.

Liga com ENCONTROS_MODO_DEMO=true. Nunca usar em produção: os CPFs abaixo entram direto.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from encontros.aplicacao.portas import Candidata, Repositorio
from encontros.dominio.perfil import DadosDoCrm, Genero, TipoDePessoa
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
    curte: Tuple[str, ...] = ()          # CPFs de quem essa pessoa já curtiu (para o match sair na hora)
    entrada: str = ""                    # o que mostrar na tela de entrada (só nas contas de teste)


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
    # perfis prontos: elas aparecem para o Lucas…
    PessoaDemo("12345678909", "Débora Martins", Genero.FEMININO, 24, "Floriano", "Centro", FLORIANO,
               hobbies=("Louvor e música", "Tocar instrumento", "Café", "Leitura bíblica", "Fotografia"),
               bio="Toco violão no ministério de louvor. Amo um café depois do culto de domingo.",
               cor=(124, 58, 237), curte=(LUCAS,)),
    PessoaDemo("98765432100", "Raquel Nunes", Genero.FEMININO, 28, "Floriano", "Sambaíba", FLORIANO,
               hobbies=("Corrida", "Academia", "Trilhas e natureza", "Viagens", "Café"),
               bio="Corro aos sábados cedo e adoro uma trilha. Sirvo na recepção.", cor=(190, 24, 93)),
    PessoaDemo("13579246828", "Sara Oliveira", Genero.FEMININO, 26, "Barão de Grajaú", "Centro", BARAO,
               hobbies=("Missões", "Voluntariado", "Ministério infantil", "Cozinhar", "Leitura bíblica"),
               bio="Sirvo no ministério infantil e sonho em fazer missões. Faço o melhor bolo de milho da cidade.",
               cor=(14, 116, 144), curte=(LUCAS,)),
    PessoaDemo("24681357928", "Lídia Carvalho", Genero.FEMININO, 23, "Floriano", "Manguinha", FLORIANO,
               hobbies=("Games", "Tecnologia", "Cinema e séries", "Idiomas"),
               bio="Desenvolvedora, gamer e fã de séries. Estudando coreano.", cor=(67, 56, 202)),
    PessoaDemo("11223344517", "Priscila Moura", Genero.FEMININO, 29, "Teresina", "Jóquei", TERESINA,
               hobbies=("Louvor e música", "Café", "Viagens", "Leitura"), bio="Ministra de louvor em Teresina.",
               cor=(161, 98, 7), curte=(LUCAS,)),
    # …e eles para a Ana
    PessoaDemo("55667788950", "Gabriel Rocha", Genero.MASCULINO, 27, "Floriano", "Centro", FLORIANO,
               hobbies=("Louvor e música", "Tocar instrumento", "Futebol", "Café"),
               bio="Baterista no louvor, zagueiro no futebol de quinta. Café sem açúcar.",
               cor=(30, 64, 175), curte=(ANA,)),
    PessoaDemo("99887766593", "Samuel Freitas", Genero.MASCULINO, 29, "Floriano", "Tiberão", FLORIANO,
               hobbies=("Leitura", "Estudos teológicos", "Café", "Idiomas"),
               bio="Professor da EBD. Sempre com um livro na mochila.", cor=(4, 120, 87)),
    PessoaDemo("44332211049", "Davi Pereira", Genero.MASCULINO, 26, "Barão de Grajaú", "Centro", BARAO,
               hobbies=("Corrida", "Ciclismo", "Trilhas e natureza", "Fotografia", "Viagens"),
               bio="Pedalo nos fins de semana e fotografo tudo pelo caminho.", cor=(194, 65, 12), curte=(ANA,)),
    PessoaDemo("10203040570", "Tiago Mendes", Genero.MASCULINO, 31, "Amarante", "Centro", AMARANTE,
               hobbies=("Louvor e música", "Cozinhar", "Pets"), bio="Líder de célula em Amarante.",
               cor=(87, 83, 78), curte=(ANA,)),
    PessoaDemo("50403020107", "Mateus Araújo", Genero.MASCULINO, 24, "Floriano", "Centro", FLORIANO,
               hobbies=("Games", "Tecnologia", "Futebol"), bio="Técnico de som da igreja.", cor=(109, 40, 217)),
)


def _membro_id(p: PessoaDemo) -> str:
    return f"demo-{p.cpf}"


def _dados(p: PessoaDemo) -> DadosDoCrm:
    return DadosDoCrm(membro_id=_membro_id(p), igreja_id=IGREJA_ID, igreja_nome=IGREJA_NOME, nome=p.nome,
                      tipo=p.tipo, genero=p.genero, idade=p.idade, estado_civil=p.estado_civil, cidade=p.cidade,
                      bairro=p.bairro, coordenadas=p.coordenadas)


class DiretorioDemo:
    async def candidatas(self, variantes_do_cpf: Sequence[str]) -> Sequence[Candidata]:
        return [Candidata(membro_id=_membro_id(p), igreja_id=IGREJA_ID, igreja_nome=IGREJA_NOME, nome=p.nome)
                for p in PESSOAS if p.cpf in set(variantes_do_cpf)]

    async def dados(self, igreja_id: str, membro_id: str) -> Optional[DadosDoCrm]:
        return next((_dados(p) for p in PESSOAS if _membro_id(p) == membro_id and igreja_id == IGREJA_ID), None)

    async def fechar(self) -> None:
        pass


def contas_de_teste() -> list:
    return [{"cpf": p.cpf, "descricao": p.entrada} for p in PESSOAS if p.entrada]


async def semear(repo: Repositorio, fotos: Fotos) -> None:
    """Cria os perfis prontos (uma vez só) e as curtidas que eles já deram."""
    if await repo.perfil(1):
        return
    ids = {}
    for p in PESSOAS:
        if p.genero is None or p.estado_civil != "solteiro" or p.tipo != TipoDePessoa.MEMBRO or p.idade < 18:
            continue
        perfil = await repo.salvar_do_crm(_dados(p))
        ids[p.cpf] = perfil.id
        if p.hobbies:
            await repo.atualizar_perfil(perfil.id, hobbies=p.hobbies, bio=p.bio,
                                        foto=fotos.gerar_de_exemplo(p.nome[0], p.cor))
    for p in PESSOAS:
        for alvo in p.curte:
            await repo.reagir(ids[p.cpf], ids[alvo], True)
    logger.info("[encontros] modo demonstração: %d perfis criados", len(ids))
