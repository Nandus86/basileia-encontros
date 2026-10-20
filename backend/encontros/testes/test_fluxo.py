"""O caminho inteiro pela API, no modo de teste (SQLite numa pasta temporária, sem Mongo, IA de mentira)."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from encontros.aplicacao.comparador import Comparador
from encontros.aplicacao.portas import Julgamento
from encontros.config import Configuracao
from encontros.container import montar
from encontros.entrada.api import criar_app
from encontros.infraestrutura.diretorio_demo import ANA, LUCAS

DEBORA = "12345678909"
LIDER = {"X-Chave-Lider": "lider-teste"}


class JevDeMentira:
    """Responde como o JEV: compatível quando há hobby igual; respostas sempre "muito parecidas"."""

    async def julgar(self, estado, perguntas):
        if "bio" in perguntas:
            return Julgamento({"bio": "improprio" if "proibido" in estado else "adequado"}, "jev")
        if "comparacao" in perguntas:
            return Julgamento({"comparacao": "muito_parecidas"}, "jev")
        if "tema" in perguntas:
            return Julgamento({"tema": "perdao"}, "jev")
        nada = "Hobbies exatamente iguais: nenhum" in estado
        return Julgamento({"afinidade": "baixa" if nada else "alta", "proximidade": "perto",
                           "apresentar": "nao" if nada else "sim"}, "jev")


@pytest.fixture
def cliente(tmp_path):
    config = Configuracao(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db", pasta_fotos=str(tmp_path / "fotos"),
                          modo_demo=True, jwt_secret="segredo-de-teste-123", openrouter_api_key="", _env_file=None)
    jev = JevDeMentira()

    async def montador(cfg):
        c = await montar(cfg)
        comparador = Comparador(jev)
        c.curadoria._julgador = jev
        c.atualizar_perfil._julgador = jev
        c.jornada._comparador = comparador
        c.conexoes._pontuacao._comparador = comparador
        return c

    with TestClient(criar_app(montador, config)) as cliente:
        yield cliente


def entrar(cliente, cpf):
    r = cliente.post("/entrar", json={"usuario": cpf, "senha": cpf})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def foto_jpg():
    saida = io.BytesIO()
    Image.new("RGB", (40, 40), (120, 40, 200)).save(saida, "JPEG")
    return saida.getvalue()


def completar(cliente, h, hobbies):
    assert cliente.put("/eu", headers=h, json={"hobbies": hobbies, "bio": "Gosto de louvor e café."}).status_code == 200
    r = cliente.post("/eu/foto", headers=h, files={"foto": ("eu.jpg", foto_jpg(), "image/jpeg")})
    assert r.status_code == 200 and r.json()["completo"]


def conexao_com(cliente, h, pontos):
    return next(x for x in cliente.get("/conexoes", headers=h).json() if x["pontos"] == pontos)


def test_so_entra_membro_solteiro_maior(cliente):
    assert "maiores de 18" in cliente.post("/entrar", json={"usuario": "33366699957", "senha": "33366699957"}).json()["detail"]
    assert "solteiros" in cliente.post("/entrar", json={"usuario": "44477700083", "senha": "44477700083"}).json()["detail"]
    assert "membros" in cliente.post("/entrar", json={"usuario": "55588811194", "senha": "55588811194"}).json()["detail"]
    assert cliente.get("/eu").status_code == 401


def test_conexoes_adiantadas_revelam_so_o_que_cada_um_escolheu(cliente):
    lucas = entrar(cliente, LUCAS)
    lista = cliente.get("/conexoes", headers=lucas).json()
    assert sorted(x["pontos"] for x in lista) == [150, 290, 390]
    for x in lista:
        assert x["outra"]["codinome"] and x["outra"]["hobbies"]
        assert x["outra"]["foto"] is False and not x["chat_aberto"]
    debora = conexao_com(cliente, lucas, 390)["outra"]     # ela revela nome com 150 e idade com 200
    assert debora["nome"] == "Débora" and debora["idade"] == 24 and debora["local"]   # bairro: 350 (padrão)
    assert debora["igreja"] is None                                                     # igreja: 450
    raquel = conexao_com(cliente, lucas, 290)["outra"]    # padrões: sobre 200, nome 250, idade 300
    assert raquel["nome"] == "Raquel" and raquel["sobre"] and raquel["idade"] is None
    sara = conexao_com(cliente, lucas, 150)["outra"]
    assert sara["nome"] is None and sara["idade"] is None and sara["sobre"] is None


def test_pergunta_a_dois_abre_o_chat_e_a_foto_so_com_liberacao(cliente):
    lucas = entrar(cliente, LUCAS)
    completar(cliente, lucas, ["Louvor e música", "Café", "Leitura bíblica"])
    con = conexao_com(cliente, lucas, 390)
    detalhe = cliente.get(f"/conexoes/{con['id']}", headers=lucas).json()
    assert detalhe["chat_abre_em"] == 400 and detalhe["nivel_dela"] is None        # sintonia ainda baixa
    pergunta = detalhe["pergunta"]["atual"]
    assert pergunta["texto"] and pergunta["minha"] is None and pergunta["dela"] is None
    assert detalhe["pergunta"]["anterior"] is None
    assert cliente.get(f"/conexoes/{con['id']}/mensagens", headers=lucas).status_code == 422   # chat fechado

    r = cliente.post(f"/conexoes/{con['id']}/pergunta", headers=lucas, json={"texto": "Fico em silêncio e oro."})
    assert r.status_code == 200 and r.json()["evento"]["pontos"] == 30
    detalhe = cliente.get(f"/conexoes/{con['id']}", headers=lucas).json()
    assert detalhe["pontos"] == 420 and detalhe["chat_aberto"]
    assert detalhe["nivel_dela"] == "Semente"                                       # sintonia ≥ 85%
    assert detalhe["pergunta"]["atual"]["texto"] != pergunta["texto"]               # a próxima (modo de teste)
    anterior = detalhe["pergunta"]["anterior"]                                      # e as duas respostas da que passou
    assert anterior["texto"] == pergunta["texto"] and anterior["minha"] and anterior["dela"]
    assert cliente.post(f"/conexoes/{con['id']}/pergunta", headers=lucas,
                        json={"texto": "me chama no zap 86 99999-1234"}).status_code == 422

    cliente.post(f"/conexoes/{con['id']}/mensagens", headers=lucas, json={"texto": "Oi! Paz!"})
    mensagens = cliente.get(f"/conexoes/{con['id']}/mensagens", headers=lucas).json()["mensagens"]
    assert [m["minha"] for m in mensagens] == [True, False]                          # o bot respondeu

    deb = entrar(cliente, DEBORA)
    lucas_id = cliente.get("/eu", headers=lucas).json()["id"]
    assert cliente.get(f"/fotos/{lucas_id}", headers=deb).status_code == 404         # foto: 450, não chegou
    assert cliente.post(f"/conexoes/{con['id']}/liberar", headers=lucas, json={"item": "foto"}).status_code == 200
    assert cliente.get(f"/fotos/{lucas_id}", headers=deb).status_code == 200


def test_sinais_do_dia_sao_poucos_e_viram_conexao(cliente):
    lucas = entrar(cliente, LUCAS)
    assert cliente.get("/sinais", headers=lucas).json()["pronto"] is False
    completar(cliente, lucas, ["Louvor e música", "Café", "Leitura bíblica", "Estudos teológicos"])
    sinais = cliente.get("/sinais", headers=lucas).json()["sinais"]
    assert 1 <= len(sinais) <= 3
    assert all(s["nome"] is None and s["idade"] is None and s["foto"] is False for s in sinais)
    assert all(s["motivos"] for s in sinais)
    ja = {x["outra"]["id"] for x in cliente.get("/conexoes", headers=lucas).json()}
    assert not ja & {s["id"] for s in sinais}                                       # quem já é conexão não volta
    r = cliente.post("/sinais", headers=lucas, json={"para_id": sinais[0]["id"], "enviar": True}).json()
    assert r["conexao"] and r["conexao"]["pontos"] >= 150                            # o bot devolveu o sinal
    assert len(cliente.get("/sinais", headers=lucas).json()["sinais"]) == len(sinais) - 1
    assert cliente.post("/sinais", headers=lucas, json={"para_id": 99999, "enviar": True}).status_code == 404


def test_jornada_devocional_e_teste_pontuam_as_conexoes(cliente):
    lucas = entrar(cliente, LUCAS)
    con = conexao_com(cliente, lucas, 150)
    j = cliente.get("/jornada", headers=lucas).json()
    assert j["devocional"]["referencia"] and j["devocional"]["minha"] is None and j["nivel"] == "Semente"
    r = cliente.post("/jornada/devocional", headers=lucas, json={"texto": "Aprendi a descansar no cuidado de Deus."})
    assert r.status_code == 200 and r.json()["ganhou"] == 10 and r.json()["sequencia"] == 1
    assert cliente.post("/jornada/devocional", headers=lucas, json={"texto": "de novo"}).status_code == 422

    teste = j["testes"][0]
    perguntas = cliente.get(f"/jornada/testes/{teste['id']}", headers=lucas).json()["lista"]
    r = cliente.post(f"/jornada/testes/{teste['id']}", headers=lucas, json={"escolhas": [0] * len(perguntas)})
    assert r.status_code == 200 and r.json()["ganhou"] == 40 and r.json()["pontos"] == 50
    tipos = [e["tipo"] for e in cliente.get(f"/conexoes/{con['id']}", headers=lucas).json()["eventos"]]
    assert "teste" in tipos and "devocional" in tipos                               # os bots também fizeram


def test_revelacoes_configuraveis(cliente):
    ana = entrar(cliente, ANA)
    eu = cliente.put("/eu/revelacoes", headers=ana, json={"limites": {"idade": 150, "foto": None}}).json()
    limites = {r["item"]: r["limite"] for r in eu["revelacoes"]}
    assert limites["idade"] == 150 and limites["foto"] is None and limites["chat"] == 400
    assert cliente.put("/eu/revelacoes", headers=ana, json={"limites": {"idade": 123}}).status_code == 422


def test_painel_do_lider(cliente):
    assert cliente.get("/lider/conteudos").status_code == 401
    pendentes = cliente.get("/lider/conteudos?status=pendente", headers=LIDER).json()
    assert {p["tipo"] for p in pendentes} == {"pergunta", "devocional"}
    pergunta = next(p for p in pendentes if p["tipo"] == "pergunta")
    r = cliente.post(f"/lider/conteudos/{pergunta['id']}/aprovar", headers=LIDER, json={})
    assert r.status_code == 200 and r.json()["status"] == "aprovado"
    assert cliente.post("/lider/gerar", headers=LIDER, json={"tipo": "pergunta"}).status_code == 422   # sem IA
    novo = cliente.post("/lider/conteudos", headers=LIDER, json={"tipo": "pergunta", "dados": {"texto": "curta"}})
    assert novo.status_code == 422
    assert cliente.get("/lider/denuncias", headers=LIDER).json() == []


def test_sem_modo_de_teste_os_perfis_de_teste_somem_dos_sinais(cliente):
    lucas = entrar(cliente, LUCAS)
    completar(cliente, lucas, ["Louvor e música", "Café", "Leitura bíblica", "Estudos teológicos"])
    c = cliente.app.state.c
    c.curadoria._perfis_de_teste = False
    cliente.portal.call(c.conexoes.mais_sinais, cliente.portal.call(c.repositorio.perfil, 1))
    assert cliente.get("/sinais", headers=lucas).json()["sinais"] == []
