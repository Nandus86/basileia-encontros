"""O caminho inteiro pela API, no modo demonstração (SQLite numa pasta temporária, sem Mongo)."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from encontros.aplicacao.curadoria import Curadoria
from encontros.aplicacao.julgamentos import PERGUNTAS_AFINIDADE
from encontros.aplicacao.portas import Julgamento
from encontros.config import Configuracao
from encontros.container import montar
from encontros.dominio.perfil import Genero
from encontros.entrada.api import criar_app
from encontros.infraestrutura.diretorio_demo import ANA, LUCAS

DEBORA, SARA, PRISCILA, GABRIEL = "12345678909", "13579246828", "11223344517", "55667788950"


class JevDeMentira:
    """Responde como o JEV: tudo compatível, menos quem não tem nenhum hobby igual."""

    def __init__(self):
        self.chamadas = 0

    async def julgar(self, estado, perguntas):
        self.chamadas += 1
        if "bio" in perguntas:
            return Julgamento({"bio": "improprio" if "proibido" in estado else "adequado"}, "jev")
        assert set(perguntas) == set(PERGUNTAS_AFINIDADE)
        nada = "Hobbies exatamente iguais: nenhum" in estado
        return Julgamento({"afinidade": "baixa" if nada else "alta", "proximidade": "perto",
                           "apresentar": "nao" if nada else "sim"}, "jev")


@pytest.fixture
def jev():
    return JevDeMentira()


@pytest.fixture
def cliente(tmp_path, jev):
    config = Configuracao(database_url=f"sqlite+aiosqlite:///{tmp_path}/t.db", pasta_fotos=str(tmp_path / "fotos"),
                          modo_demo=True, jwt_secret="segredo-de-teste-123", _env_file=None)

    async def montador(cfg):
        c = await montar(cfg)
        c.curadoria = Curadoria(c.repositorio, jev)
        c.conversas._curadoria = c.curadoria
        c.atualizar_perfil._julgador = jev
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
    r = cliente.put("/eu", headers=h, json={"hobbies": hobbies, "bio": "Gosto de louvor e café."})
    assert r.status_code == 200, r.text
    r = cliente.post("/eu/foto", headers=h, files={"foto": ("eu.jpg", foto_jpg(), "image/jpeg")})
    assert r.status_code == 200 and r.json()["completo"]


def test_so_entra_membro_solteiro_maior(cliente):
    assert "maiores de 18" in cliente.post("/entrar", json={"usuario": "33366699957", "senha": "33366699957"}).json()["detail"]
    assert "solteiros" in cliente.post("/entrar", json={"usuario": "44477700083", "senha": "44477700083"}).json()["detail"]
    assert "membros" in cliente.post("/entrar", json={"usuario": "55588811194", "senha": "55588811194"}).json()["detail"]
    assert cliente.post("/entrar", json={"usuario": LUCAS, "senha": "123"}).status_code == 403
    assert cliente.get("/eu").status_code == 401


def test_do_descobrir_ao_match_e_a_foto_liberada(cliente, jev):
    lucas = entrar(cliente, LUCAS)
    assert cliente.get("/descobrir", headers=lucas).json() == {"pronto": False, "cartoes": []}
    completar(cliente, lucas, ["Louvor e música", "Café", "Leitura bíblica", "Missões"])

    cartoes = cliente.get("/descobrir", headers=lucas).json()["cartoes"]
    nomes = [c["nome"] for c in cartoes]
    assert "Débora" in nomes and "Sara" in nomes
    assert "Priscila" not in nomes                     # Teresina: fora do raio
    assert "Lídia" not in nomes                        # nenhum hobby igual
    assert all("foto" not in c for c in cartoes)       # o cartão nunca leva foto
    debora = next(c for c in cartoes if c["nome"] == "Débora")
    assert debora["em_comum"] and debora["afinidade"]["nivel"] == "alta"

    chamadas = jev.chamadas
    cliente.get("/descobrir", headers=lucas)
    assert jev.chamadas == chamadas                    # a afinidade guardada é reaproveitada

    # a Débora já tinha curtido: match na hora
    match = cliente.post("/reacoes", headers=lucas, json={"para_id": debora["id"], "curtiu": True}).json()["match"]
    assert match and match["pessoa"]["nome"] == "Débora"
    assert "Débora" not in [c["nome"] for c in cliente.get("/descobrir", headers=lucas).json()["cartoes"]]

    # a foto dela continua escondida até ela liberar
    assert cliente.get(f"/fotos/{debora['id']}", headers=lucas).status_code == 404
    deb = entrar(cliente, DEBORA)
    cliente.post(f"/matches/{match['id']}/mensagens", headers=deb, json={"texto": "Oi, Lucas! Paz!"})
    assert cliente.get("/matches", headers=lucas).json()[0]["nao_lidas"] == 1
    assert cliente.post(f"/matches/{match['id']}/liberar-foto", headers=deb).status_code == 200
    r = cliente.get(f"/fotos/{debora['id']}", headers=lucas)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    meu = cliente.get("/matches", headers=deb).json()[0]
    assert meu["eu_liberei"] and not meu["foto_liberada"]

    lidas = cliente.get(f"/matches/{match['id']}/mensagens", headers=lucas).json()["mensagens"]
    assert [m["texto"] for m in lidas] == ["Oi, Lucas! Paz!"] and not lidas[0]["minha"]
    cliente.post(f"/matches/{match['id']}/lido", headers=lucas, json={"ate": lidas[-1]["id"]})
    assert cliente.get("/matches", headers=lucas).json()[0]["nao_lidas"] == 0

    # desfazer: some a conversa e a foto volta a ficar escondida
    assert cliente.delete(f"/matches/{match['id']}", headers=lucas).status_code == 200
    assert cliente.get("/matches", headers=lucas).json() == []
    assert cliente.get(f"/fotos/{debora['id']}", headers=lucas).status_code == 404


def test_curtir_sem_afinidade_e_recusado(cliente):
    lucas = entrar(cliente, LUCAS)
    completar(cliente, lucas, ["Louvor e música", "Café", "Leitura bíblica"])
    todos = cliente.portal.call(cliente.app.state.c.repositorio.perfis, list(range(1, 30)))
    lidia = next(p for p in todos.values() if p.nome.startswith("Lídia"))
    r = cliente.post("/reacoes", headers=lucas, json={"para_id": lidia.id, "curtiu": True})
    assert r.status_code == 409


def test_bio_moderada(cliente):
    ana = entrar(cliente, ANA)
    r = cliente.put("/eu", headers=ana, json={"bio": "me chama no insta @ana"})
    assert r.status_code == 422 and "conversa acontece aqui" in r.json()["detail"]
    r = cliente.put("/eu", headers=ana, json={"bio": "texto proibido"})
    assert r.status_code == 422
    assert cliente.put("/eu", headers=ana, json={"bio": "Amo trilhas e louvor."}).status_code == 200


def test_ana_ve_os_rapazes_perto(cliente):
    ana = entrar(cliente, ANA)
    completar(cliente, ana, ["Louvor e música", "Tocar instrumento", "Corrida", "Trilhas e natureza"])
    nomes = [c["nome"] for c in cliente.get("/descobrir", headers=ana).json()["cartoes"]]
    assert {"Gabriel", "Davi"} <= set(nomes)
    assert "Tiago" not in nomes                        # Amarante, ~60 km
    eu = cliente.get("/eu", headers=ana).json()
    assert eu["genero"] == Genero.FEMININO.value and eu["nome_publico"] == "Ana"
