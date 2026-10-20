# Basiléia Encontros — 0.0.2 (jornada e mistério)

App (web mobile, instalável como PWA) para **membros solteiros e maiores de idade** das igrejas no Basiléia
se conhecerem por **afinidade**, aos poucos. Ninguém aparece pelo nome: cada pessoa é um **codinome** (Cedro Sereno,
Lírio Fiel…) e, no começo, só os **interesses** ficam visíveis. Nome, idade, bairro, foto, igreja e o chat são
revelados conforme a **afinidade da dupla** cresce, nos limites que cada um escolhe.

> A versão anterior (estilo "match") está no branch `0.0.1`.

```
[App Next.js (frontend/)] ──HTTP──▶ [API FastAPI + LangGraph (backend/)] ──▶ Postgres (tabelas encontros_*)
                                              │   ├──▶ Mongo do CRM (só leitura: cadastro dos membros)
                                              │   └──▶ OpenRouter: JEV (afinidade, comparação de respostas,
                                              │        temas, moderação) e um modelo de texto (gera conteúdo)
                                              └── fotos em disco (volume), servidas só com permissão
```

## Como funciona

**Dois placares**

| | Jornada (da pessoa) | Afinidade (da dupla) |
|---|---|---|
| Sobe com | devocional diário (+10, mais bônus por dias seguidos), testes (+40), pergunta a dois (+5) | os dois responderem a mesma coisa de forma parecida |
| Serve para | nível (Semente → Broto → Raiz → Árvore → Fruto), mais sinais por dia, análise mais funda | revelar o que cada um escolheu e abrir o chat |

1. **Entrar** — CPF + CPF conferido no Mongo do CRM (acesso **provisório**, o mesmo do mensageiro). Só entra
   **membro**, **18+** e **solteiro** pelo cadastro; quem casou ou foi desativado some na hora.
2. **Cadastro** — hobbies, "sobre mim" (moderado), foto (obrigatória, escondida), **o que revelar e com quantos
   pontos** (padrão: sobre 200, nome 250, idade 300, bairro 350, chat 400, foto 450, igreja 450; ou "só na mão")
   e preferências de idade e distância.
3. **Sinais do dia** — poucas pessoas por dia (3; 4 no nível Raiz; 5 no Fruto), escolhidas uma vez por dia:
   - regras duras (gênero, idade que cada um aceita, distância) e o **JEV** julgando hobbies e localização
     (grafo do LangGraph em [curadoria.py](backend/encontros/aplicacao/curadoria.py));
   - a ordem e os motivos ficam mais fundos com o que a pessoa já respondeu: **testes em comum** (valores) e
     **temas dos devocionais** ([conexoes.py](backend/encontros/aplicacao/conexoes.py), `_aprofundar`).
   O cartão mostra só codinome, símbolo, interesses e o motivo ("Responderam parecido em ‘Igreja e serviço’").
4. **Conexão** — os dois enviaram sinal. Começa com 150–200 pontos (pela afinidade de hobbies) e já soma o que
   os dois tinham respondido em comum.
5. **Pergunta a dois** — uma por dia por conexão. Cada um só vê a resposta do outro depois de responder; o JEV
   compara (muito parecidas +30, parecidas +20, complementares +15, diferentes +5). Devocional do mesmo dia vale
   metade; teste em comum, até +50 (as opções são uma escala, então 1 e 2 estão mais perto que 1 e 4).
6. **Revelações** — cada item aparece quando a dupla chega no limite de quem revela, ou quando a pessoa libera na
   mão naquela conexão. O **chat** precisa dos dois: vale o **maior** limite. A foto continua sem link público.
   O nível de jornada da outra pessoa só aparece com **sintonia ≥ 85%** (a média de tudo que a dupla comparou).
7. **Líder** (`/lider`, com a chave `ENCONTROS_CHAVE_LIDER`) — a IA gera devocionais, perguntas e testes como
   **pendentes**; o líder revisa, edita, aprova ou recusa. Nada gerado chega aos membros sem aprovação. Os testes
   são de **estilo** (reservado ↔ expansivo…), nunca de certo e errado. O painel também lista as denúncias.
   O conteúdo inicial (8 devocionais, 12 perguntas, 3 testes, escritos à mão) entra como pendente em produção.

## Rodando no computador

**Modo de teste** (`ENCONTROS_MODO_DEMO=true`): contas de teste, conteúdo já aprovado e perfis que **jogam
sozinhos** — devolvem o sinal, respondem a pergunta a dois, o devocional e os testes logo depois de você e
respondem no chat. Quem entra ganha **3 conexões adiantadas (150, 290 e 390 pontos)** para testar as revelações,
não há limite de uma pergunta por dia e aparece o botão "Mais sinais". Os perfis de teste aparecem para qualquer
cidade. Se o `ENCONTROS_MONGO_URI` também estiver configurado, **os CPFs reais entram junto** (cada um com o seu
cadastro). A chave do líder, se não for configurada, é `lider-teste`. Sem Mongo nem chave da OpenRouter também roda:

```bash
# API
cd backend
py -3.11 -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
cp .env.example .env                 # já vem com ENCONTROS_MODO_DEMO=true
.venv/Scripts/python -m encontros    # http://localhost:8020/docs

# App
cd frontend
npm install
npm run dev                          # http://localhost:3020 (abra no celular pelo IP da máquina)
```

Na tela de entrada aparecem as contas de teste: **Lucas** e **Ana** (perfis para completar — algumas pessoas
já curtiram os dois, então o match sai na hora), e Pedro (17), Marcos (casado) e Júlia (visitante), que não entram.

**Segredos locais**: a API também lê o `.env.test` da raiz (fora do git), por cima do `backend/.env`.
Ali vai `OPENROUTER_API_KEY=...` (liga o JEV). Para entrar com um **CPF real**, desligue a demonstração
e aponte para o CRM no mesmo arquivo:

```
ENCONTROS_MODO_DEMO=false
ENCONTROS_MONGO_URI=mongodb://...      # o usuário só de leitura do Motor de Cuidado
ENCONTROS_IGREJAS=*                    # ou o id da sua igreja
```

Com Docker: `docker compose up -d --build` (Postgres + API + app). Para o app no celular, use
`NEXT_PUBLIC_API_BASE=http://IP-DA-MAQUINA:8020` e coloque esse endereço do app em `ENCONTROS_ORIGENS`.

Testes: `cd backend && .venv/Scripts/python -m pytest -q`

## Easypanel

Dois serviços **App** a partir deste repositório (fonte GitHub, build por Dockerfile), mais um Postgres.

**1. `encontros-api`**
- Caminho de build: `/backend` · Dockerfile: `Dockerfile` · porta **8000**
- **Volume** em `/app/dados` (as fotos ficam aqui; sem volume, somem a cada deploy)
- Domínio público, ex.: `encontros-api.seudominio` → porta 8000
- Variáveis:

```
ENCONTROS_DATABASE_URL=postgres://usuario:senha@NOME-DO-POSTGRES:5432/banco?sslmode=disable   # a URL do Easypanel, como vem
ENCONTROS_MONGO_URI=mongodb://...            # o usuário só de leitura do Motor de Cuidado
ENCONTROS_MONGO_DB=dexos_basileia
ENCONTROS_IGREJAS=*                          # ou os ids das igrejas de teste
ENCONTROS_JWT_SECRET=um-segredo-novo-e-longo
ENCONTROS_ORIGENS=https://encontros.seudominio
ENCONTROS_OPENROUTER_API_KEY=sk-or-...
ENCONTROS_ESTADOS_CIVIS=solteiro
ENCONTROS_CHAVE_LIDER=uma-chave-para-a-lideranca
ENCONTROS_MODO_DEMO=true                     # fase de testes: perfis que jogam sozinhos + CPFs reais
```

As tabelas e colunas novas são criadas sozinhas ao subir (não precisa apagar o banco da 0.0.1).

**2. `encontros-app`**
- Caminho de build: `/frontend` · Dockerfile: `Dockerfile` · porta **3000**
- **Argumento de build** (não variável de execução): `NEXT_PUBLIC_API_BASE=https://encontros-api.seudominio`
  (o endereço fica gravado no app; se mudar, faça um novo deploy)
- Domínio público, ex.: `encontros.seudominio` → porta 3000

Para testar sem o CRM no servidor, troque as variáveis do Mongo por `ENCONTROS_MODO_DEMO=true`
(o SQLite e as fotos ficam no volume). HTTPS é obrigatório para o celular liberar a localização e instalar o app.

## Variáveis da API (`ENCONTROS_*`)

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` (pode ser o Postgres do Basile; as tabelas começam com `encontros_`). Padrão: SQLite local |
| `MONGO_URI` / `MONGO_DB` | o mesmo usuário **só de leitura** do Motor de Cuidado / `dexos_basileia` |
| `IGREJAS` | ids das igrejas liberadas, separados por vírgula (`*` = todas) |
| `JWT_SECRET` | segredo novo e longo, só deste app |
| `ORIGENS` | endereço do app (CORS) |
| `ESTADOS_CIVIS` | quem pode usar. Padrão `solteiro`; dá para incluir `viuvo,divorciado` se a igreja quiser |
| `IDADE_MINIMA` | padrão 18 |
| `OPENROUTER_API_KEY` | chave da OpenRouter (JEV e reserva). Sem ela, a afinidade é só por hobbies iguais |
| `MODELO_JEV` / `MODELO_RESERVA` | `~typesafe/jev-latest` / `deepseek/deepseek-v4.1-flash` |
| `PASTA_FOTOS` | onde as fotos ficam (volume persistente) |
| `MODO_DEMO` | `true` = modo de teste (contas e perfis que jogam sozinhos). **Desligar antes de abrir ao público** |
| `CHAVE_LIDER` | a chave do painel `/lider` (sem ela, o painel fica desligado; no modo de teste: `lider-teste`) |
| `MODELO_ESCRITOR` | modelo que gera devocionais, perguntas e testes (padrão `deepseek/deepseek-v4.1-flash`) |

App: `NEXT_PUBLIC_API_BASE` (no build) — endereço da API.

## Estrutura

```
backend/encontros/
├── dominio/          regras puras: quem entra, perfil, afinidade; jornada.py (níveis, pontos, revelações, codinomes)
├── aplicacao/        casos de uso: entrar, perfil, curadoria (LangGraph), conexoes (sinais, revelações, pergunta
│                     a dois, chat), jornada (devocional, testes), pontuacao, comparador, conteudo (líder + IA)
├── infraestrutura/   SQL (SQLAlchemy + sincronização de colunas), CRM (Mongo), OpenRouter (JEV, reserva,
│                     escritor), fotos, tokens, conteudo_semente, diretorio_demo (modo de teste e bots)
├── entrada/          api.py + rotas_perfil, rotas_conexoes, rotas_jornada, rotas_lider
└── testes/
frontend/src/
├── app/              entrar, boas-vindas (6 passos), sinais, conexoes, conexoes/[id], jornada,
│                     jornada/teste/[id], perfil, lider
├── components/       avatar com símbolo e cadeado, trilha de pontos, campos do perfil (revelações), estrutura
├── contexts/         sessão
└── lib/              cliente da API, tema claro/escuro
```

## Limites do MVP (próximos passos)

- **Senha = CPF** é fraca (herdada do mensageiro). Antes de abrir para todas as igrejas: senha de verdade ou código
  por WhatsApp (o disparador já existe).
- Chat por consulta a cada 3 s (simples e leve). Com mais gente: WebSocket + Redis, como no mensageiro.
- Sem notificação push; limite de tentativas em memória (uma cópia só da API).
- Denúncias ficam na tabela `encontros_denuncias`, sem painel ainda: falta a tela para a liderança analisar.
- Tabelas criadas com `create_all`; quando o esquema mudar, passar para migrações.
- Idade e estado civil vêm do CRM: se o cadastro estiver errado, a pessoa é orientada a falar com a secretaria.
