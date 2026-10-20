"""As perguntas fechadas que o JEV responde, e como as respostas viram decisões do app."""
from __future__ import annotations

from typing import Mapping

from encontros.aplicacao.portas import Pergunta
from encontros.dominio.afinidade import Afinidade, Nivel, Proximidade
from encontros.dominio.jornada import TEMAS

PERGUNTAS_AFINIDADE = {
    "afinidade": Pergunta(
        "Quanto os hobbies e interesses das duas pessoas combinam? Conte os iguais e também os parecidos "
        "(ex.: corrida e academia; tocar instrumento e louvor; trilhas e ciclismo). Leve em conta o 'sobre'.",
        {"alta": "Vários interesses iguais ou muito parecidos; teriam muito o que fazer e conversar juntas",
         "media": "Alguns interesses em comum ou parecidos",
         "baixa": "Quase nada em comum"}),
    "proximidade": Pergunta(
        "As duas pessoas moram perto o bastante para se encontrar com facilidade (no culto, na célula, num café)?",
        {"perto": "Mesma cidade ou até uns 15 km",
         "razoavel": "Mais longe, mas dentro da distância que as duas aceitam",
         "longe": "Fora da distância que alguma delas aceita, ou cidades diferentes sem saber a distância"}),
    "apresentar": Pergunta(
        "Pelas características das duas (interesses e localização), vale apresentar uma à outra?",
        {"sim": "Têm interesses em comum de verdade e moram perto o bastante",
         "nao": "Pouca afinidade ou longe demais"}),
}

PERGUNTAS_BIO = {
    "bio": Pergunta(
        "O texto 'sobre mim' é adequado para um perfil num app de relacionamento cristão, só para membros de igreja?",
        {"adequado": "Fala da pessoa, dos gostos, da fé ou do que procura, com respeito",
         "contato": "Passa telefone, @ de rede social, e-mail ou link para conversar fora do app",
         "improprio": "Conteúdo sexual, ofensivo, discriminatório, venda ou propaganda"}),
}

PERGUNTA_COMPARAR = Pergunta(
    "Compare as respostas das duas pessoas à mesma pergunta. Elas pensam e vivem a fé de um jeito parecido?",
    {"muito_parecidas": "Dizem quase a mesma coisa, com a mesma visão e o mesmo tom",
     "parecidas": "Visão parecida, com palavras ou exemplos diferentes",
     "complementares": "Ângulos diferentes que se completam, sem conflito",
     "diferentes": "Visões ou prioridades diferentes, ou uma delas quase não respondeu"})

PERGUNTA_TEMA = Pergunta("Qual é o tema principal do que a pessoa escreveu?", TEMAS)

MOTIVOS_BIO = {
    "contato": "Tire telefone, @ ou links do texto: a conversa acontece aqui dentro, quando a conexão liberar o chat.",
    "improprio": "Esse texto não combina com o app. Escreva sobre você, seus gostos e o que procura.",
}


def afinidade_das_respostas(respostas: Mapping[str, str], em_comum, origem: str) -> Afinidade:
    return Afinidade(nivel=Nivel(respostas["afinidade"]), proximidade=Proximidade(respostas["proximidade"]),
                     apresentar=respostas["apresentar"] == "sim", em_comum=tuple(em_comum), origem=origem)
