# Spec: LinguaBot --- English Teacher Telegram Bot

> **Versao:** 2.0 (refinado via 5 rodadas de entrevista)
> **Ultima atualizacao:** 26 de Junho de 2026

---

## 1. Visao Geral

### 1.1 Proposito
Assistente pessoal de ingles via Telegram --- um bot que atua como professor particular para falantes de portugues brasileiro em nivel iniciante (A1-A2).

### 1.2 Nome do Bot
**LinguaBot** --- nome ja definido para o bot no Telegram.

### 1.3 Publico-Alvo
- Brasileiros aprendendo ingles do zero (A1-A2)
- Uso individual, apenas chats privados (1:1) --- sem suporte a grupos
- Frequencia: leve a moderada (algumas dezenas de mensagens por dia)

---

## 2. Stack Tecnologica

| Camada                | Tecnologia                                              | Justificativa                                       |
| --------------------- | ------------------------------------------------------- | --------------------------------------------------- |
| Linguagem             | Python 3.11+                                            | Maturidade, ecossistema, simplicidade para o projeto|
| Gerenciador de Pacotes | pip + venv                                              | Simplicidade, ja vem com Python                     |
| Bot Framework         | python-telegram-bot v20+ (async)                        | Padrao da comunidade, suporte a inline keyboards    |
| Webhook Server        | FastAPI + Uvicorn (para deploy no Render)               | Necessario para manter servico ativo no free tier   |
| LLM                   | Google Gemini (google-generativeai SDK)                 | Escolhido pelo usuario                              |
| STT (pos-MVP)         | Deepgram (free tier)                                    | Entrada de audio                                    |
| TTS (pos-MVP)         | ElevenLabs (free tier)                                  | Saida de audio                                      |
| Banco de Dados (dev)  | SQLite (via sqlite3 padrao do Python)                   | Persistencia de vocabulario, zero configuracao      |
| Banco de Dados (prod) | PostgreSQL via Supabase (free tier, recomendado)        | Render tem filesystem efemero, Supabase e gratuito e persistente |
| Hospedagem            | Render (Web Service)                                    | Free tier com webhook, deploy via GitHub            |
| Estado da Conversa    | In-memory (nao persiste entre restarts do bot)          | 10-15 mensagens de contexto por sessao              |
| Testes                | pytest + mocks (AsyncMock)                              | Testes unitarios com mocks do Telegram              |

---

## 3. Arquitetura do Projeto

```
english-teacher-bot/
|-- .env.example                    # Template de variaveis de ambiente
|-- .gitignore
|-- README.md                       # Guia de setup, deploy e uso
|-- requirements.txt                # Dependencias Python
|-- runtime.txt                     # Versao do Python para o Render
|-- bot/
|   |-- __init__.py
|   |-- main.py                     # Entrypoint --- polling (dev) ou webhook (prod)
|   |-- config.py                   # Carrega variaveis de ambiente
|   |-- database.py                 # Abstraco de BD --- SQLite (dev) ou PostgreSQL (prod)
|   |-- webhook_server.py           # Servidor FastAPI para webhook (Render) + health check
|   |-- handlers/
|   |   |-- __init__.py
|   |   |-- start.py                # /start --- boas-vindas + menu inicial
|   |   |-- help.py                 # /help --- instrucoes e comandos
|   |   |-- message.py              # Conversaco em texto (LLM)
|   |   |-- error_handler.py        # Tratamento global de erros
|   |   |-- commands.py             # /reset, /vocab, /topic
|   |-- services/
|   |   |-- __init__.py
|   |   |-- gemini.py               # Integraco com Google Gemini
|   |   |-- deepgram.py             # STT (pos-MVP)
|   |   |-- elevenlabs.py           # TTS (pos-MVP)
|   |   |-- conversation.py         # Gerenciamento de contexto da conversa
|   |-- utils/
|   |   |-- __init__.py
|   |   |-- formatting.py           # Formataco de mensagens, quebra de texto longo
|   |   |-- rate_limiter.py         # Controle de limite diario (soft limit)
|   |   |-- keyboards.py            # Menus e botoes inline
|-- tests/
|   |-- __init__.py
|   |-- conftest.py                 # Fixtures e mocks compartilhados
|   |-- test_gemini.py              # Testes do servico Gemini
|   |-- test_conversation.py        # Testes do gerenciamento de contexto
|   |-- test_rate_limiter.py        # Testes do limite de uso
|   |-- test_handlers.py            # Testes dos handlers com mocks do Telegram
```

---

## 4. Funcionalidades Detalhadas

### 4.1 MVP (v1.0) --- Apenas Texto

#### 4.1.1 Comandos

| Comando    | Descricao                                                                                   | Implementacao                         |
| ---------- | ------------------------------------------------------------------------------------------- | ------------------------------------- |
| /start     | Mensagem de boas-vindas + menu inicial com botoes inline                                    | handler start.py + keyboards.py       |
| /help      | Lista de comandos disponiveis + dicas de uso                                                | handler help.py                       |
| /reset     | Limpa o historico da conversa atual (novo inicio)                                           | handler commands.py + conversation.py |
| /vocab     | Mostra lista de vocabulario aprendido (persistente), com botao "Ver mais"                   | handler commands.py + database.py     |
| /topic     | Bot sugere um topico aleatorio da lista fixa para praticar                                 | handler commands.py                   |

#### 4.1.2 Conversaco Livre com Correcoes
- Usuario envia mensagem de texto ---> bot responde em ingles
- Gemini recebe: historico da conversa (10-15 ultimas mensagens) + system prompt
- Correco contextual gentil de erros (max 1-2 correcoes por mensagem)
- Imersao total: bot responde APENAS em ingles

#### 4.1.3 Botoes Interativos (Inline Keyboards)
Durante a conversa, o bot oferece botoes contextuais:
- **"More Examples"** --- Gemini gera mais exemplos da palavra/estrutura atual
- **"Explain This Word"** --- Explicaco simples da palavra destacada
- **"Practice This"** --- Pequeno exercicio de fixaco sobre o topico atual

#### 4.1.4 Sugesto Automatica de Topicoss
- Bot sugere um topico da **lista fixa** quando:
  - A conversa esta comecando (apos /start ou /reset)
  - O usuario usa /topic
- Formato: "Let's practice a topic! How about **Food & Drinks**? Would you like to talk about your favorite foods?"
- Topicoss sao sugeridos de forma nao intrusiva, respeitando o fluxo natural

#### 4.1.5 Vocabulario Persistente (SQLite/PostgreSQL)
- **Tabela:** vocabulary
  - id (INTEGER PRIMARY KEY AUTOINCREMENT)
  - user_id (INTEGER NOT NULL)
  - word (TEXT NOT NULL) --- palavra em ingles
  - translation (TEXT NOT NULL) --- traduco em portugues
  - context (TEXT) --- frase de exemplo onde foi apresentada
  - created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
  - reviewed_at (TIMESTAMP) --- ultima revisao
  - practice_count (INTEGER DEFAULT 0) --- quantas vezes praticada
  - UNIQUE(user_id, word) --- evitar duplicatas por usuario

- Vocabulario e salvo automaticamente quando o Gemini introduz uma nova palavra
- /vocab mostra **todo o historico** ordenado por data (mais recente primeiro)
- Limite de exibico: 10 palavras por vez, com botao "Ver mais" (paginado)

#### 4.1.6 Lista Fixa de Topicoss (15 Iniciais)

| #  | Topico (ingles)     | Topico (portugues)     | Vocabulario-chave sugerido                        |
| -- | ------------------- | ---------------------- | ------------------------------------------------- |
| 1  | Greetings           | Saudacoes              | Hello, Good morning, How are you?, Nice to meet   |
| 2  | Food & Drinks       | Comida e Bebida        | Breakfast, lunch, dinner, water, rice, bread      |
| 3  | Family              | Familia                | Mother, father, brother, sister, baby             |
| 4  | Weather             | Clima                  | Sunny, rainy, cold, hot, windy, cloudy            |
| 5  | Daily Routine       | Rotina Diaria          | Wake up, eat, work, sleep, shower, brush          |
| 6  | Animals             | Animais                | Dog, cat, bird, fish, horse, cow                  |
| 7  | Numbers & Colors    | Numeros e Cores        | One-ten, red, blue, green, yellow, black, white   |
| 8  | Shopping            | Compras                | Buy, sell, price, cheap, expensive, money         |
| 9  | Transport           | Transporte             | Car, bus, train, bike, airport, station           |
| 10 | Body & Health       | Corpo e Saude          | Head, hand, foot, doctor, sick, hospital          |
| 11 | House & Furniture   | Casa e Moveis          | Room, kitchen, bed, table, chair, door, window    |
| 12 | Work & School       | Trabalho e Escola      | Teacher, student, office, homework, class         |
| 13 | Clothes & Seasons   | Roupas e Estacoes      | Shirt, pants, shoes, summer, winter, spring       |
| 14 | Hobbies & Games     | Hobbies e Jogos        | Read, play, run, sing, dance, game, music         |
| 15 | Places in the City  | Lugares na Cidade      | Park, market, library, bank, restaurant, museum   |

#### 4.1.7 Limite Suave de Uso (Rate Limiter)
- **100 mensagens/dia por usuario** (reset a meia-noite UTC)
- O bot avisa o usuario ao atingir **80%** (80 mensagens):
  - "You've almost reached your daily practice limit! You have 20 more messages today. Great job practicing! :)"
- Ao atingir 100 mensagens:
  - "You've reached your daily practice limit! Come back tomorrow to continue learning. Keep up the great work! :star:"
  - O bot nao bloqueia --- apenas avisa. O usuario pode continuar, mas o aviso se repete a cada mensagem.
- Implementaco: dicionario em memoria com persistencia opcional em arquivo JSON

#### 4.1.8 Indicador de Digitaco
- Bot usa chat_action="typing" enquanto aguarda resposta do Gemini
- Para respostas longas, o indicador permanece ativo ate o fim do processamento

---

## 5. System Prompt (para o Gemini)

```
You are an enthusiastic and patient English teacher for beginner (A1-A2)
students. Your student is a Brazilian Portuguese speaker learning English.

RULES:
1. ALWAYS respond in English only --- full immersion. Never use Portuguese.
2. Use simple vocabulary and short sentences (A1-A2 level).
3. When the student makes a mistake, gently correct:
   - Acknowledge what they got right first
   - Offer the correction with a brief, simple explanation
   - Max 1-2 corrections per message --- don't overwhelm
4. Encourage often --- celebrate their efforts with positive reinforcement.
5. If they use Portuguese, gently redirect to English:
   "Try saying that in English! I know you can do it! :muscle:"
6. Introduce new relevant vocabulary naturally during conversation.
   When you introduce a new word, format it for vocab extraction:
   NEW_WORD: [word] = [translation]
   EXAMPLE: [simple sentence using the word]
7. Keep responses conversational, engaging, and varied.
8. Tone: balanced --- friendly and encouraging like a friend, but with
   teacher-like clarity when correcting mistakes.
9. Use emojis sparingly but warmly.
```

---

## 6. Tratamento de Erros

### 6.1 Estrategia Geral
- **Retry automatico:** 1-2 tentativas com backoff de 2 segundos antes de mostrar erro ao usuario
- Se todas as tentativas falharem, mostrar mensagem amigavel em ingles:
  - "Sorry, I'm having trouble thinking right now. Let's try again in a moment! :hourglass:"
- Logging: apenas print() statements por enquanto (logging sera adicionado em versao futura)

### 6.2 Cenarioss Especificos

| Cenarioss                          | Comportamento                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| Gemini API timeout (5s+)          | Tentar novamente 1x. Se falhar, avisar usuario                                     |
| Gemini quota excedida             | Avisar e sugerir voltar mais tarde                                                 |
| SQLite/DB erro de escrita         | Logar erro, ignorar salvamento de vocabulario, continuar conversa                  |
| Mensagem muito longa (>4000 chars)| Quebrar em multiplas mensagens usando formatting.py                                |
| Usuario envia comando invalido    | Mensagem: "I don't know this command. Try /help to see what I can do! :smile:"     |
| Usuario envia midia nao suportada | Mensagem: "I can only read text messages for now. Type something and let's talk!"  |

---

## 7. Interface do Bot

### 7.1 Menu Inicial (/start)
```
:wave: Hello! I'm LinguaBot, your English teacher!

I'm here to help you practice English. We can talk about many topics,
and I'll gently correct your mistakes along the way.

[Start a Conversation] [How it Works]
```

### 7.2 Botoes Inline Pos-Resposta
Apos cada resposta do bot, o usuario ve:
```
[More Examples] [Explain This Word] [Practice This]
```

### 7.3 /vocab Output
```
:books: Your Vocabulary (12 words)

1. breakfast = cafe da manha
   "I eat breakfast at 7am."
   :star: Practiced 3 times

2. weather = clima / tempo
   "The weather is sunny today."
   :star: Practiced 1 time

[Show More --->]
```

---

## 8. Polling vs Webhook --- Estrategia de Deploy

### 8.1 O Problema
O **Render free tier** tem uma limitaco critica: servicos Web desligam (spin down) apos **15 minutos de inatividade**. Como um bot Telegram usando **polling** mantem apenas conexoes de saida (bot ---> Telegram), o Render interpreta isso como "inativo" e desliga o processo.

### 8.2 Soluco: Webhook com FastAPI
Para manter o bot ativo no free tier, usamos **webhooks** em produco:

| Aspecto                | Polling (dev local)                    | Webhook (produco/Render)              |
| ---------------------- | -------------------------------------- | ------------------------------------- |
| Conexo                 | Bot busca updates ativamente           | Telegram envia updates para o bot     |
| Trafego                | Apenas saida (bot ---> Telegram)       | Entrada (Telegram ---> bot) = atividade |
| Spin down              | Sim --- Render desliga apos 15min      | Nao --- trafego HTTP mantem ativo     |
| Start Command          | python main.py                         | uvicorn bot.webhook_server:app --host 0.0.0.0 --port $PORT |
| Rota adicional         | Nenhuma                                | GET /health para monitoramento        |
| Config. env            | BOT_MODE=polling                       | BOT_MODE=webhook + RENDER_URL=...     |

### 8.3 Fallback: Health Check + UptimeRobot
Caso o webhook tenha problemas, um fallback opcional:
- Bot roda em modo polling
- UptimeRobot (free) pinga https://app.onrender.com/health a cada 5 minutos
- Isso impede o spin down artificialmente
- **Nao recomendado:** fragil, sujeito a cold starts e viola o espirito do free tier

### 8.4 Implementaco
- webhook_server.py contem uma aplicaco FastAPI separada
- main.py detecta BOT_MODE da env var e inicializa no modo apropriado
- O servidor webhook escuta na porta fornecida pelo Render ($PORT, geralmente 10000)
- O webhook e registrado automaticamente via bot.application.run_webhook()
- GET /health retorna {"status": "ok", "timestamp": ...}

---

## 9. Persistencia de Dados no Render

### 9.1 O Problema
O Render free tier tem um **filesystem efemero** --- qualquer arquivo salvo localmente (incluindo SQLite .db) e **apagado** sempre que o servico reinicia ou faz deploy.

### 9.2 Soluco para Desenvolvimento Local
- **SQLite** continua sendo usado em ambiente de desenvolvimento local
- Banco fica em bot/data/vocabulary.db (adicionar ao .gitignore)
- Simples, zero configuracao, ideal para testes

### 9.3 Soluco para Produco (Render)
Duas opcoes gratuitas e persistentes de PostgreSQL externo:

| Criterio               | Supabase (free tier, recomendado)                      | Neon (free tier, alternativa)                      |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------------- |
| **Persistencia**       | Sim (sem expiracao)                                    | Sim (sem expiracao)                                |
| **Armazenamento**      | 500 MB por projeto                                     | 0.5 GB por projeto                                |
| **Comportamento ocioso** | Pausa apos 1 semana sem atividade                    | Scale to zero (acorda mais rapido)                |
| **Conexao**             | Connection pooler incluso + Auth nativo                | Conexao direta via TLS                            |
| **Extras**             | Auth, Storage, Edge Functions, Realtime                 | Branching, DB branching                           |
| **Setup**              | Criar projeto, pegar connection string                 | Criar projeto, pegar connection string            |

**Recomendacao para o MVP:** **Supabase** -- ja vai preparar o terreno para futuras features (auth, storage) mesmo que nao sejam usadas agora.

**Alternativa:** **Neon** -- mais rapido para acordar de idle, puramente PostgreSQL.

### 9.4 Abstraco de Banco de Dados
- database.py tera duas implementacoes:
  - SQLiteDatabase --- para dev local
  - PostgresDatabase --- para produco (Render)
- Ambas implementam a mesma interface
- A escolha e feita via env var DATABASE_URL:
  - Se vazio ---> usa SQLite
  - Se definido ---> usa PostgreSQL na URL fornecida
- Dependencia: psycopg2-binary ou asyncpg no requirements.txt

---

## 10. Fases de Implementaco

### Fase 1 --- Setup (Projeto Base)
- Criar estrutura de diretorios
- requirements.txt: python-telegram-bot[job-queue]>=20.0, google-generativeai>=0.8.0, fastapi, uvicorn
- .env.example com: BOT_TOKEN, GEMINI_API_KEY, DATABASE_URL, BOT_MODE, RENDER_URL
- config.py --- carregar variaveis via os.getenv()
- main.py --- inicializaco do bot com polling (modo dev)
- .gitignore (Python padrao + .env + *.db)
- runtime.txt: python-3.11.0
- Handler /start com menu inicial
- Handler /help com instrucoes

### Fase 2 --- Gemini + Conversaco
- services/gemini.py --- cliente Gemini, com retry automatico
- services/conversation.py --- gerenciamento de contexto (10-15 mensagens)
- handlers/message.py --- receber mensagens de texto, chamar Gemini, responder
- database.py --- abstracao de BD: SQLiteDatabase
- Salvamento automatico de vocabulario das respostas do Gemini
- System prompt completo

### Fase 3 --- UX e Comandos
- handlers/commands.py --- /reset, /vocab, /topic
- utils/keyboards.py --- todos os botoes inline
- utils/formatting.py --- quebra de mensagens longas, formataco de vocabulario
- utils/rate_limiter.py --- soft limit de 100 mensagens/dia
- Botoes "More Examples", "Explain This Word", "Practice This"
- Sugesto automatica de topicoss da lista fixa

### Fase 4 --- Testes
- tests/conftest.py --- fixtures e mocks (AsyncMock para Telegram, mock para Gemini)
- tests/test_gemini.py --- testar chamadas e retry
- tests/test_conversation.py --- testar gerenciamento de contexto
- tests/test_rate_limiter.py --- testar soft limit
- tests/test_handlers.py --- testar handlers com mocks do Telegram

### Fase 5 --- Webhook e Deploy
- webhook_server.py --- servidor FastAPI (POST /webhook, GET /health)
- main.py --- modo dual: polling (dev) ou webhook (prod) via BOT_MODE
- database.py --- adicionar PostgresDatabase (usando asyncpg)
- .env.example atualizado com DATABASE_URL
- README.md com guia completo de deploy

### Fase 6 --- Audio (pos-MVP)
- services/deepgram.py --- STT via Deepgram
- services/elevenlabs.py --- TTS via ElevenLabs
- handlers/audio.py --- receber audio, transcrever, responder com texto + audio
- Comando /voice --- alternar entre resposta texto e texto+audio

---

## 11. Variaveis de Ambiente

```
# .env --- LinguaBot Configuration

# Telegram (obrigatorio --- criar via @BotFather)
BOT_TOKEN=your_telegram_bot_token_here

# Google Gemini (obrigatorio --- https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# Modo de operaco (polling para dev, webhook para produco)
BOT_MODE=polling

# Render (obrigatorio apenas em modo webhook)
RENDER_URL=https://your-app.onrender.com

# Deepgram (opcional, pos-MVP --- https://deepgram.com/)
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# ElevenLabs (opcional, pos-MVP --- https://elevenlabs.io/)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Banco de Dados (vazio = SQLite local, URL = PostgreSQL externo)
DATABASE_URL=

# Configuracoes (opcionais, com defaults)
DAILY_LIMIT=100
MAX_HISTORY_TURNS=15
GEMINI_MODEL=gemini-2.0-flash
```

---

## 12. Decisoes de Design (Registro de Decisoes Tecnicas)

| #  | Deciso                                     | Alternativa Rejeitada             | Motivo                                                                |
| -- | ------------------------------------------ | --------------------------------- | --------------------------------------------------------------------- |
| 1  | SQLite (dev) + PostgreSQL (prod)            | Apenas SQLite                     | Render filesystem efemero exige BD externo em produco                 |
| 2  | pip + venv                                 | Poetry / uv                       | Simplicidade maxima para projeto pequeno                              |
| 3  | Render como hospedagem                     | Railway / Fly.io                  | Preferencia explicita do usuario                                      |
| 4  | Retry automatico com backoff (2x)          | Fallback offline / sem retry      | Gemini e barato o suficiente para retentar                           |
| 5  | Lista fixa de topicoss (15)                | Topicoss gerados por Gemini       | Consistencia e previsibilidade para nivel A1-A2                       |
| 6  | Soft limit (100 msg/dia) nao bloqueante    | Sem limites / Limite duro         | Proteger custos sem frustrar o usuario                                |
| 7  | In-memory para contexto da conversa        | SQLite para tudo                  | Performance, contexto nao precisa sobreviver a restart                |
| 8  | Testes com mocks desde o MVP               | Testes unitarios apenas           | Garantir que handlers do Telegram funcionem corretamente              |
| 9  | Imersao total em ingles (bot so fala ingles) | Bot bilingue                    | Melhor metodo de aprendizado para A1-A2                               |
| 10 | Webhook em produco (FastAPI)               | Polling + UptimeRobot             | Webhook e a unica forma confiavel de evitar spin down no Render       |
| 11 | PostgreSQL via Supabase (recomendado)                   | Neon / Render PostgreSQL free (30 dias) | Render PostgreSQL expira em 30 dias; Supabase e gratuito e persistente |
| 12 | Vocabulario de todo o historico no /vocab  | Apenas da sessao atual            | Reviso e essencial para aprendizado de longo prazo                   |
| 13 | Tom balanceado (amigo + professor)         | Amigo only / Professor only       | Acolhedor mas com autoridade pedagogica                               |
| 14 | Abstraco de BD (interface dupla)          | BD unico fixo                     | Permite SQLite em dev e PostgreSQL em prod sem mudar codigo           |

---

## 13. MVP Checklist (v1.0)

- [ ] Projeto configurado (estrutura, requirements, .env, .gitignore, runtime.txt)
- [ ] Bot responde a /start e /help com menus
- [ ] Conversaco livre com Gemini (texto)
- [ ] Correco contextual de erros
- [ ] /reset e /vocab funcionando
- [ ] Vocabulario persistente (SQLite em dev, PostgreSQL em prod)
- [ ] Botoes inline (More Examples, Explain This Word, Practice This)
- [ ] Sugesto automatica de topicoss da lista fixa
- [ ] Rate limiter (soft limit de 100 msg/dia)
- [ ] Testes unitarios com mocks (pytest)
- [ ] Webhook + FastAPI para Render
- [ ] Deploy no Render
- [ ] README com guia de setup e deploy

---

## 14. Glossario

| Termo                 | Definico                                                                    |
| --------------------- | --------------------------------------------------------------------------- |
| A1-A2                 | Niveis iniciante e basico do CEFR (Common European Framework of Reference)  |
| Inline Keyboard       | Botoes do Telegram que aparecem dentro da conversa, abaixo da mensagem      |
| Soft Limit            | Limite de uso que avisa o usuario mas nao bloqueia                          |
| Polling               | Metodo do bot verificar constantemente se ha novas mensagens                |
| Webhook               | Metodo alternativo onde o Telegram chama o bot quando ha mensagem           |
| Token (Gemini)        | Unidade de medida de entrada/saida do modelo (~1 token ~= 4 caracteres)     |
| Turn                  | Uma troca de mensagens (usuario envia ---> bot responde)                    |
| System Prompt         | Instruco inicial para o modelo de IA definir comportamento e regras        |
| Spin Down             | Recursos do servico sao liberados apos periodo de inatividade               |
| Ephemeral Filesystem  | Sistema de arquivos temporario que e limpo em restart/deploy                |

---

## 15. Consideracoes Futuras (pos-MVP)

- [ ] Entrada e saida de audio (Deepgram + ElevenLabs)
- [ ] Suporte a imagens (upload de foto para descrever)
- [ ] Feedback do usuario (avaliar correcoes como util/não util)
- [ ] Estatisticas de progresso (dias seguidos, palavras aprendidas, erros comuns)
- [ ] Flashcards de reviso (baseado no vocabulario salvo)
- [ ] Modo de conversa guiada (licoes passo a passo)
- [ ] Logging estruturado com rotaco de arquivos
- [ ] Multiplos niveis de dificuldade (B1, B2 futuramente)
- [ ] Comando /stats --- estatisticas do usuario
- [ ] Comando /pronounce --- ouvir pronuncia de palavras
