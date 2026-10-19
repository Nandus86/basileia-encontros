# Basiléia Encontros — MVP

App (web mobile, instalável como PWA) para **membros solteiros e maiores de idade** das igrejas no Basiléia
se conhecerem por **afinidade**. A foto fica escondida: só aparece na conversa, depois do match,
quando a própria pessoa libera.

```
[App Next.js (frontend/)] ──HTTP──▶ [API FastAPI + LangGraph (backend/)] ──▶ Postgres (tabelas encontros_*)
                                              │   ├──▶ Mongo do CRM (só leitura: cadastro dos membros)
                                              │   └──▶ OpenRouter: JEV (afinidade e moderação da bio)
                                              └── fotos em disco (volume), servidas só com permissão
```

## Como funciona

1. **Entrar** — CPF + CPF, conferido no Mongo do CRM (o mesmo acesso **provisório** do app de conversa/mensageiro,
   até combinar uma senha de verdade com o dev do CRM). Tentativas limitadas e só igrejas liberadas.
   A cada entrada o cadastro é lido de novo e só entra quem é **membro** (não visitante/contato, não desativado),
   **18+** (data de nascimento do CRM), **solteiro** (estado civil do CRM; cônjuge ligado no cadastro = casado)
   e com gênero no cadastro. Quem casou ou foi desativado sai do Descobrir na hora.
2. **Perfil** — dados do CRM (nome, idade, cidade, localização) + o que a pessoa escolhe no app:
   hobbies (mínimo 3, de um catálogo), "sobre mim" (moderado), foto (obrigatória, mas escondida) e preferências
   (idade, distância). Para os outros aparece só o **primeiro nome** e a distância **arredondada** (a ~5 km).
3. **Descobrir** — grafo do LangGraph ([curadoria.py](backend/encontros/aplicacao/curadoria.py)):
   - `buscar_candidatos`: regras duras nos dois sentidos — gênero oposto, idade que **cada um** aceita, distância
     dentro do raio dos dois (sem localização: só a mesma cidade). Sem IA.
   - `separar_conhecidas`: a afinidade de cada par fica guardada e só é julgada de novo se algum dos dois perfis mudar.
   - `julgar`: o **JEV** (`~typesafe/jev-latest`, endpoint `alpha/decisions` da OpenRouter, mesmo cliente do Motor de
     Cuidado) responde 3 perguntas fechadas sobre o par: `afinidade` (alta/média/baixa — conta hobbies iguais e
     *parecidos*, ex.: corrida e academia), `proximidade` (perto/razoável/longe) e `apresentar` (sim/não).
     Se o JEV falhar → reserva por LLM pedindo JSON → por último, regras (só hobbies iguais).
   - `montar_feed`: só os **compatíveis** (as "mesmas características"), os de mais afinidade primeiro.
4. **Curtir / passar** — curtir só vale para quem o Descobrir mostraria (o servidor confere a afinidade guardada).
   Curtida dos dois lados = **match**.
5. **Conversa** — só com match. Cada um tem o botão **Liberar minha foto** (vale para aquela conversa, sem volta).
   A foto não tem link público: a API só entrega para a própria pessoa ou para quem tem match ativo **e** recebeu a
   liberação. Toda foto é reprocessada no servidor (tira o EXIF, que pode ter o GPS de casa).
   Dá para **desfazer o match** e **denunciar** (encerra a conversa e esconde um do outro).

## Rodando no computador

**Modo demonstração** (sem Mongo nem chave da OpenRouter; CRM de mentira com perfis prontos em Floriano-PI):

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
ENCONTROS_DATABASE_URL=postgresql+asyncpg://usuario:senha@NOME-DO-POSTGRES:5432/banco
ENCONTROS_MONGO_URI=mongodb://...            # o usuário só de leitura do Motor de Cuidado
ENCONTROS_MONGO_DB=dexos_basileia
ENCONTROS_IGREJAS=*                          # ou os ids das igrejas de teste
ENCONTROS_JWT_SECRET=um-segredo-novo-e-longo
ENCONTROS_ORIGENS=https://encontros.seudominio
ENCONTROS_OPENROUTER_API_KEY=sk-or-...
ENCONTROS_ESTADOS_CIVIS=solteiro
```

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
| `MODO_DEMO` | `true` só no computador — **nunca em produção** |

App: `NEXT_PUBLIC_API_BASE` (no build) — endereço da API.

## Estrutura

```
backend/encontros/
├── dominio/          regras puras: quem entra, perfil, distância, afinidade por regras
├── aplicacao/        casos de uso: entrar, perfil (+ moderação), curadoria (LangGraph), conversas; perguntas do JEV
├── infraestrutura/   SQL (SQLAlchemy), CRM (Mongo), JEV/OpenRouter, fotos, tokens, CRM de demonstração
├── entrada/api.py    rotas FastAPI
└── testes/
frontend/src/
├── app/              entrar, boas-vindas (cadastro em 5 passos), descobrir, conversas, conversas/[id], perfil
├── components/       cartão deslizável, avatar com cadeado, campos do perfil, estrutura (abas, botões)
├── contexts/         sessão
└── lib/              cliente da API, tema claro/escuro
```

## Limites do MVP (próximos passos)

- **Senha = CPF** é fraca (herdada do mensageiro). Antes de abrir para todas as igrejas: senha de verdade ou código
  por WhatsApp (o disparador já existe).
- Conversa por consulta a cada 3 s (simples e leve). Com mais gente: WebSocket + Redis, como no mensageiro.
- Sem notificação push; limite de tentativas em memória (uma cópia só da API).
- Denúncias ficam na tabela `encontros_denuncias`, sem painel ainda: falta a tela para a liderança analisar.
- Tabelas criadas com `create_all`; quando o esquema mudar, passar para migrações.
- Idade e estado civil vêm do CRM: se o cadastro estiver errado, a pessoa é orientada a falar com a secretaria.
