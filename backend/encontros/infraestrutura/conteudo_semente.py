"""Conteúdo inicial (escrito à mão, não pela IA). No modo de teste já entra aprovado; em produção entra como
pendente, para o líder revisar antes de publicar. Os versículos aparecem só pela referência."""
from __future__ import annotations

DEVOCIONAIS = (
    {"titulo": "O pastor que cuida", "referencia": "Salmos 23:1-3",
     "reflexao": "Davi conhecia o trabalho de pastor: guiar, proteger, levar para onde há água e descanso. "
                 "Quando ele diz que nada lhe falta, não está dizendo que tem tudo o que quer, mas que está perto de "
                 "quem sabe do que ele precisa. Em dias corridos, é fácil achar que tudo depende de nós. Hoje, antes "
                 "de resolver a próxima coisa da lista, pare um minuto e lembre: você tem um Pastor. Ele conhece o "
                 "caminho, o ritmo e os pastos verdes que você ainda não viu.",
     "pergunta": "Em que área da sua vida você mais precisa descansar no cuidado de Deus agora?"},
    {"titulo": "Ansiosos por nada", "referencia": "Filipenses 4:6-7",
     "reflexao": "Paulo escreve da prisão e fala de paz. Ele não nega os problemas: troca a ansiedade por oração, "
                 "e a oração vem junto com gratidão. A paz que ele promete não depende de tudo dar certo; ela guarda "
                 "o coração enquanto as coisas ainda estão sendo resolvidas. Ansiedade quer controlar o amanhã; "
                 "oração entrega o amanhã a quem já está lá. Que tal transformar a sua maior preocupação de hoje em "
                 "uma conversa sincera com Deus?",
     "pergunta": "O que você costuma fazer quando a ansiedade aperta? O que gostaria de fazer diferente?"},
    {"titulo": "Amor que age", "referencia": "1 Coríntios 13:4-7",
     "reflexao": "Este texto é lido em casamentos, mas foi escrito para uma igreja cheia de conflitos. O amor que "
                 "Paulo descreve não é sentimento bonito: é paciência na fila, bondade com quem não retribui, "
                 "humildade para não querer ter razão sempre. Antes de pensar em encontrar alguém que nos ame assim, "
                 "a pergunta é se estamos aprendendo a amar assim — na família, na célula, no trabalho.",
     "pergunta": "Qual dessas características do amor é mais difícil para você viver hoje?"},
    {"titulo": "Raízes junto às águas", "referencia": "Jeremias 17:7-8",
     "reflexao": "A árvore plantada junto às águas também passa pelo calor e pela seca. A diferença está nas raízes: "
                 "ela continua verde porque bebe de uma fonte que não seca. Ninguém vê as raízes, mas são elas que "
                 "sustentam o que todos veem. Os hábitos escondidos — oração, Palavra, comunhão — são as nossas raízes. "
                 "Eles não aparecem no perfil de ninguém, mas mostram o seu valor no tempo difícil.",
     "pergunta": "Qual hábito escondido tem sustentado a sua fé ultimamente?"},
    {"titulo": "Setenta vezes sete", "referencia": "Mateus 18:21-22",
     "reflexao": "Pedro achou que estava sendo generoso ao propor perdoar sete vezes. Jesus responde com um número que "
                 "quer dizer: pare de contar. Perdoar não é fingir que não doeu nem voltar a confiar de imediato; é "
                 "desistir de cobrar a dívida. Quem foi muito perdoado aprende a perdoar. Às vezes a pessoa mais "
                 "difícil de perdoar somos nós mesmos.",
     "pergunta": "Perdoar é mais difícil para você quando a ofensa vem de quem? Por quê?"},
    {"titulo": "Um propósito para cada tempo", "referencia": "Eclesiastes 3:1-8",
     "reflexao": "Há tempo de plantar e tempo de colher, tempo de chorar e tempo de dançar. A sabedoria está em "
                 "reconhecer em que tempo estamos, sem querer pular etapas. Solteiro, casado, estudando, recomeçando: "
                 "cada fase tem algo que só se aprende nela. Em vez de apenas esperar a próxima estação, pergunte o "
                 "que Deus quer formar em você nesta.",
     "pergunta": "O que você sente que Deus está ensinando para você nesta fase da vida?"},
    {"titulo": "Servir com o que se tem", "referencia": "João 6:8-11",
     "reflexao": "André apresentou um menino com cinco pães e dois peixes e logo duvidou: o que é isso para tanta "
                 "gente? Jesus não pediu mais; pediu o que havia. O milagre começou com alguém disposto a entregar o "
                 "pouco. Muitas vezes deixamos de servir porque achamos que o nosso talento é pequeno demais. Nas "
                 "mãos de Jesus, o pouco entregue alimenta multidões.",
     "pergunta": "Que 'pães e peixes' você tem para oferecer no serviço à igreja ou ao próximo?"},
    {"titulo": "Melhor serem dois", "referencia": "Eclesiastes 4:9-12",
     "reflexao": "O texto fala de amizade, trabalho e caminhada: quando um cai, o outro levanta. Deus nos fez para a "
                 "comunhão, e ninguém foi chamado para viver a fé sozinho. O cordão de três dobras lembra que os "
                 "relacionamentos mais firmes têm Deus no meio. Antes de procurar alguém, vale cultivar amizades "
                 "verdadeiras, que nos levantem e que nós possamos levantar.",
     "pergunta": "Quem tem sido um 'segundo' na sua caminhada? E para quem você tem sido?"},
)

PERGUNTAS = (
    "O que você faz quando Deus parece em silêncio?",
    "Qual versículo te acompanha há mais tempo, e por quê?",
    "Como seria um domingo perfeito para você?",
    "O que você mais admira na igreja onde congrega?",
    "Que hábito cristão você quer criar ou retomar este ano?",
    "Como você descreveria a sua fé para alguém que não conhece Jesus?",
    "Qual foi um momento em que você viu Deus agir de um jeito inesperado?",
    "O que significa servir para você?",
    "Como você lida com uma opinião diferente da sua dentro da igreja?",
    "Que lugar a família ocupa nos seus planos para o futuro?",
    "Qual livro, pregação ou louvor marcou você recentemente?",
    "O que você gostaria que as pessoas sentissem depois de passar um tempo com você?",
)

TESTES = (
    {"titulo": "Como eu vivo a fé no dia a dia", "tema": "devoção", "questoes": [
        {"texto": "Meu tempo com Deus costuma ser…",
         "opcoes": ["Todos os dias, num horário fixo", "Quase todo dia, quando dá", "Algumas vezes por semana",
                    "Mais nos cultos e na célula"]},
        {"texto": "Quando leio a Bíblia, prefiro…",
         "opcoes": ["Um plano de leitura completo", "Um livro por vez, com calma", "Devocionais curtos",
                    "Trechos que alguém indica"]},
        {"texto": "Minha oração é mais…",
         "opcoes": ["Silenciosa, a sós", "Conversada, ao longo do dia", "Em grupo, com outras pessoas",
                    "Cantada, no louvor"]},
        {"texto": "Jejum para mim é…",
         "opcoes": ["Prática frequente", "Algo para momentos especiais", "Algo que quero aprender",
                    "Pouco presente na minha vida"]},
        {"texto": "Falo da minha fé com quem não é da igreja…",
         "opcoes": ["Sempre que surge a chance", "Quando perguntam", "Mais pelo exemplo que por palavras",
                    "Ainda tenho dificuldade"]},
    ]},
    {"titulo": "Igreja e serviço", "tema": "comunidade", "questoes": [
        {"texto": "Na igreja, eu me vejo mais…",
         "opcoes": ["Servindo num ministério toda semana", "Ajudando quando chamam", "Participando de célula ou grupo",
                    "Ainda procurando meu lugar"]},
        {"texto": "Um culto bom para mim tem mais…",
         "opcoes": ["Palavra profunda", "Equilíbrio entre Palavra e louvor", "Louvor e adoração",
                    "Comunhão e acolhimento"]},
        {"texto": "Sobre missões e ação social…",
         "opcoes": ["Quero ir ou já fui", "Contribuo e oro", "Ajudo em ações locais", "É algo que quero conhecer"]},
        {"texto": "Minha célula ou pequeno grupo é…",
         "opcoes": ["Essencial, não fico sem", "Importante, vou quase sempre", "Vou de vez em quando",
                    "Ainda não participo"]},
        {"texto": "Quando há um conflito na igreja, eu…",
         "opcoes": ["Procuro a pessoa para conversar", "Peço conselho à liderança", "Oro e espero esfriar",
                    "Prefiro me afastar um pouco"]},
    ]},
    {"titulo": "Planos, família e futuro", "tema": "futuro", "questoes": [
        {"texto": "Família, para mim, é…",
         "opcoes": ["A prioridade dos meus planos", "Muito importante, junto com o chamado",
                    "Importante, mas sem pressa", "Algo que entrego nas mãos de Deus"]},
        {"texto": "Num relacionamento, a vida espiritual juntos deve ser…",
         "opcoes": ["O centro: orar e ler juntos", "Presente, com igreja e célula juntos",
                    "Cada um com a sua, se apoiando", "Algo que se constrói com o tempo"]},
        {"texto": "Sobre dinheiro, eu sou mais…",
         "opcoes": ["Planejador, com metas e reserva", "Organizado, mas flexível", "Vivo um mês de cada vez",
                    "Generoso, às vezes demais"]},
        {"texto": "Meu tempo livre ideal é…",
         "opcoes": ["Em casa, tranquilo", "Com poucos amigos próximos", "Com muita gente, na igreja ou fora",
                    "Viajando e conhecendo lugares"]},
        {"texto": "Quando penso no futuro, sinto mais…",
         "opcoes": ["Paz, confio no tempo de Deus", "Expectativa boa", "Um pouco de ansiedade", "Muitas dúvidas"]},
    ]},
)

# o que entra para o líder aprovar no modo de teste (para testar a tela de aprovação)
PENDENTES_DE_EXEMPLO = (
    ("pergunta", {"texto": "Se você pudesse passar um dia com um personagem bíblico, quem seria e o que perguntaria?"}),
    ("devocional", {"titulo": "A fé que espera", "referencia": "Hebreus 11:1",
                    "reflexao": "Fé é confiar no que ainda não se vê. Abraão saiu sem saber para onde ia; "
                                "Noé construiu a arca antes da chuva. Esperar com fé não é ficar parado: é seguir "
                                "obedecendo enquanto a promessa não chega. O que parece demora pode ser preparo. "
                                "Hoje, lembre de uma promessa de Deus e dê um passo de obediência nela.",
                    "pergunta": "Que promessa você ainda está esperando, e como tem esperado?"}),
)

# respostas dos perfis de teste, por jeito de ser (assim umas duplas combinam mais que outras)
JEITOS = ("contemplativo", "servidor", "alegre")

RESPOSTAS_DOS_BOTS = {
    "contemplativo": (
        "Procuro ficar em silêncio e voltar para a Palavra. Os Salmos me ajudam muito nessas horas, e tento confiar "
        "que Deus continua trabalhando mesmo quando eu não percebo.",
        "Gosto de começar o dia em oração, com calma. Para mim a fé é um relacionamento, um tempo a sós com Deus que "
        "depois transborda para o resto do dia.",
        "Valorizo muito a família e quero construir um lar com Deus no centro, com oração juntos e muita paciência.",
    ),
    "servidor": (
        "Quando Deus parece em silêncio eu continuo servindo. Ajudar alguém me lembra que Ele está agindo, e no "
        "ministério eu vejo Deus de perto.",
        "Fé para mim é colocar a mão na massa: servir na igreja, ajudar o próximo, estar disponível. Aprendo muito "
        "servindo com outras pessoas.",
        "Quero uma família que sirva junto, que abra a casa para receber pessoas e que participe da igreja ativamente.",
    ),
    "alegre": (
        "Coloco um louvor e converso com Deus do jeito que estou. Também chamo um amigo para orar comigo, porque "
        "comunhão me fortalece muito.",
        "Minha fé é muito ligada à gratidão e ao louvor. Gosto de celebrar o que Deus faz e de estar com gente, na "
        "célula e nos cultos.",
        "Família é alegria! Quero uma casa cheia, com amigos, louvor e muita comunhão, sempre com Deus no meio.",
    ),
}

ESCOLHAS_DOS_BOTS = {"contemplativo": 0, "servidor": 1, "alegre": 2}   # a opção "base" de cada jeito nos testes

MENSAGENS_DOS_BOTS = (
    "Que bom que o chat abriu! 😊 Gostei muito das suas respostas nas perguntas.",
    "Verdade! Me conta mais: em que ministério você serve?",
    "Amém! Também penso assim. Qual louvor tem tocado você ultimamente?",
    "Haha, que legal. Bom falar com alguém que pensa parecido 🙏",
)
