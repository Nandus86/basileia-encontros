from datetime import date

from encontros.dominio.afinidade import Nivel, Proximidade, afinidade_por_regras, assinatura, podem_se_ver
from encontros.dominio.perfil import (DadosDoCrm, Genero, Perfil, TipoDePessoa, bio_tem_contato,
                                      distancia_aproximada, estado_civil_de, idade_em, limpar_hobbies,
                                      motivo_para_nao_entrar, primeiro_nome)

SOLTEIROS = frozenset({"solteiro"})


def dados(**mudancas):
    base = dict(membro_id="m1", igreja_id="i1", igreja_nome="Igreja", nome="Ana Souza", tipo=TipoDePessoa.MEMBRO,
                genero=Genero.FEMININO, idade=25, estado_civil="solteiro")
    base.update(mudancas)
    return DadosDoCrm(**base)


def perfil(id, genero=Genero.FEMININO, idade=25, hobbies=("Café", "Corrida", "Leitura"), coordenadas=(-6.7669, -43.0225),
           **mudancas):
    return Perfil(id=id, membro_id=f"m{id}", igreja_id="i1", igreja_nome="Igreja", nome=f"Pessoa {id}", genero=genero,
                  idade=idade, cidade="Floriano", coordenadas=coordenadas, hobbies=hobbies, tem_foto=True, **mudancas)


def test_idade_nos_formatos_do_crm():
    hoje = date(2026, 10, 19)
    assert idade_em("2000-10-19", hoje) == 26
    assert idade_em("20/10/2008", hoje) == 17
    assert idade_em("20-10-2000", hoje) == 25
    assert idade_em("", hoje) is None


def test_estado_civil_e_nome():
    assert estado_civil_de("SOLTEIRA") == "solteiro"
    assert estado_civil_de("Casado(a)") == "casado"
    assert estado_civil_de("União Estável") == "uniao_estavel"
    assert primeiro_nome("  ana  beatriz souza") == "Ana"


def test_quem_pode_entrar():
    assert motivo_para_nao_entrar(dados(), SOLTEIROS) is None
    assert "maiores de 18" in motivo_para_nao_entrar(dados(idade=17), SOLTEIROS)
    assert "solteiros" in motivo_para_nao_entrar(dados(estado_civil="casado"), SOLTEIROS)
    assert "membros" in motivo_para_nao_entrar(dados(tipo=TipoDePessoa.VISITANTE), SOLTEIROS)
    assert "membros" in motivo_para_nao_entrar(dados(desativado=True), SOLTEIROS)
    assert "nascimento" in motivo_para_nao_entrar(dados(idade=None), SOLTEIROS)
    assert "gênero" in motivo_para_nao_entrar(dados(genero=None), SOLTEIROS)
    assert motivo_para_nao_entrar(dados(estado_civil="viuvo"), frozenset({"solteiro", "viuvo"})) is None


def test_regras_duras_nos_dois_sentidos():
    ela, ele = perfil(1), perfil(2, genero=Genero.MASCULINO, idade=30)
    assert podem_se_ver(ela, ele) and podem_se_ver(ele, ela)
    assert not podem_se_ver(ela, perfil(3))                                   # mesmo gênero
    assert not podem_se_ver(ela.com(idade_max=28), ele)                       # fora da idade que ela aceita
    assert not podem_se_ver(ela, ele.com(idade_min=26))                       # fora da idade que ele aceita
    longe = ele.com(coordenadas=(-5.0920, -42.8038))                          # Teresina, ~190 km
    assert not podem_se_ver(ela, longe)
    assert not podem_se_ver(ela, ele.com(tem_foto=False))                     # perfil incompleto
    assert not podem_se_ver(ela, ele.com(visivel=False))
    sem_local = ele.com(coordenadas=None)
    assert podem_se_ver(ela, sem_local)                                       # sem localização: mesma cidade
    assert not podem_se_ver(ela, sem_local.com(cidade="Amarante"))


def test_afinidade_por_regras():
    ela = perfil(1, hobbies=("Café", "Corrida", "Leitura", "Viagens"))
    ele = perfil(2, genero=Genero.MASCULINO, hobbies=("Café", "Corrida", "Leitura"))
    a = afinidade_por_regras(ela, ele)
    assert a.nivel == Nivel.ALTA and a.proximidade == Proximidade.PERTO and a.compativel
    pouco = afinidade_por_regras(ela, ele.com(hobbies=("Games", "Tecnologia", "Café")))
    assert pouco.nivel == Nivel.BAIXA and not pouco.compativel


def test_assinatura_e_simetrica_e_muda_com_o_perfil():
    ela, ele = perfil(1), perfil(2, genero=Genero.MASCULINO)
    assert assinatura(ela, ele) == assinatura(ele, ela)
    assert assinatura(ela, ele) != assinatura(ela.com(bio="nova"), ele)


def test_bio_com_contato_e_hobbies_do_catalogo():
    assert bio_tem_contato("me chama no zap 86 99999-1234")
    assert bio_tem_contato("segue lá @ana.souza")
    assert bio_tem_contato("www.meusite.com")
    assert not bio_tem_contato("Amo louvor, café e trilhas. Sirvo na recepção há 3 anos.")
    assert limpar_hobbies(["Café", "Inventado", "Corrida", "Café"]) == ("Corrida", "Café")


def test_distancia_arredondada():
    assert distancia_aproximada(1.2) == 5
    assert distancia_aproximada(12.1) == 15
    assert distancia_aproximada(None) is None
