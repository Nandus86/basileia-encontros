from datetime import date

from encontros.dominio.jornada import (chat_aberto, chat_abre_em, limiares, nivel_de, nova_sequencia,
                                       pontos_do_devocional, profundidade, revelou, semelhanca_das_escolhas,
                                       temas_por_palavras)


def test_niveis_e_sinais_por_dia():
    assert nivel_de(0).nome == "Semente" and nivel_de(0).proximo_em == 100
    assert nivel_de(260).nome == "Raiz" and nivel_de(260).sinais_por_dia == 4
    assert nivel_de(5000).proximo is None


def test_sequencia_de_devocionais():
    hoje = date(2026, 10, 20)
    assert nova_sequencia(None, hoje, 0) == 1
    assert nova_sequencia("2026-10-19", hoje, 3) == 4          # ontem: continua
    assert nova_sequencia("2026-10-20", hoje, 3) == 3          # hoje de novo: igual
    assert nova_sequencia("2026-10-17", hoje, 9) == 1          # pulou: recomeça
    assert pontos_do_devocional(1) == 10 and pontos_do_devocional(4) == 16 and pontos_do_devocional(30) == 20


def test_revelacoes_e_chat_pelo_maior_limite():
    eu, ela = limiares({"chat": 400, "idade": 300}), limiares({"chat": 300})
    assert revelou("idade", eu, (), 300) and not revelou("idade", eu, (), 299)
    assert revelou("foto", eu, {"foto"}, 0)                    # liberada na mão
    assert not chat_aberto(eu, (), ela, (), 350)               # ela já liberaria, eu ainda não
    assert chat_aberto(eu, (), ela, (), 400)
    assert chat_abre_em(eu, (), ela, ()) == 400
    assert chat_abre_em(limiares({"chat": None}), (), ela, ()) is None     # só na mão
    assert limiares({"chat": 123, "nada": 1})["chat"] == 400               # inválido volta ao padrão


def test_semelhanca_dos_testes_e_profundidade():
    assert semelhanca_das_escolhas([0, 1, 2], [0, 1, 2]) == 1
    assert semelhanca_das_escolhas([0], [3]) == 0
    assert round(semelhanca_das_escolhas([0, 0], [1, 0]), 3) == round((2 / 3 + 1) / 2, 3)
    assert profundidade(0, 0, 0) == 40 and profundidade(10, 50, 50) == 95
    assert "perdao" in temas_por_palavras("Aprendi a perdoar quem me magoou")
