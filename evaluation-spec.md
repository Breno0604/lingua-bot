# Spec: Avaliação de Qualidade — LinguaBot

> **Versao:** 1.0
> **Data:** 27 de Junho de 2026
> **Tipo:** Avaliacao Geral de Qualidade (Analise Completa)
> **Projeto:** LinguaBot — English Teacher Telegram Bot

---

## Sumario Executivo

O LinguaBot e um bot Telegram para ensino de ingles a brasileiros, construido **integralmente por IA** sob orientacao de um desenvolvedor intermediario. O projeto esta **funcional e rodando** (1 usuario — o proprio desenvolvedor), com **96 testes passando** e codigo bem estruturado em camadas (handlers/services/utils).

### Notas Gerais

| Dimensao | Nota | Status Geral |
|----------|------|-------------|
| **Codigo & Arquitetura** | **B+** | Bem organizado, padroes consistentes, mas com oportunidades de melhoria |
| **Testes & Confiabilidade** | **A-** | Cobertura solida, mocks bem feitos, 96/96 passando |
| **UX do Bot** | **B+** | Experiencia boa, mas faltam refinamentos e feedback visual |
| **Prontidao para Producao** | **C+** | Funciona, mas varios riscos e lacunas para uso real |
| **Documentacao** | **B** | README excelente, specs detalhadas, comentarios no codigo inconsistentes |
| **Seguranca** | **B** | Chaves em .env, mas sem validacoes robustas de entrada |

**Nota Geral: B/B+** — Projeto solido para MVP, com boa arquitetura e testes. Os maiores riscos estao em prontidao para producao e tratamento de erros em runtime.

---

## 1. Codigo & Arquitetura — Nota: B+

### 1.1 Estrutura Geral

```
bot/
├── main.py                  # Entrypoint + DI container (build_application)
├── config.py                # Config centralizada (dataclass + dotenv)
├── database.py              # Abstracao de BD (ABC + 2 implementacoes)
├── webhook_server.py        # FastAPI para webhook
├── handlers/                # Logica de comandos e callbacks
│   ├── start.py             # /start
│   ├── help.py              # /help
│   ├── commands.py          # /reset, /vocab, /topic
│   ├── level_command.py     # /level
│   ├── callbacks.py         # Botoes inline
│   ├── message.py           # Mensagens de texto + extracao vocab
│   └── error_handler.py     # Tratamento global de erros
├── services/                # Logica de negocios
│   ├── groq.py              # Cliente LLM (Groq)
│   ├── conversation.py      # Gerenciamento de contexto
│   └── level_manager.py     # Niveis de proficiencia
└── utils/                   # Utilitarios
    ├── formatting.py        # Formatacao de texto/topicos/vocab
    ├── keyboards.py         # Botoes inline
    └── rate_limiter.py      # Rate limiting
```

**Pontos Fortes:**
- Separacao clara em camadas (handlers/servicos/util)
- Injecao de dependencia manual via `bot_data` (simples e eficaz)
- `build_application()` como factory — reusavel em polling e webhook
- Database com ABC e duas implementacoes (SQLite + Supabase)
- Config como dataclass com validacao

**Oportunidades de Melhoria:**
| Item | Problema | Sugestao |
|------|----------|----------|
| Injeção de dependencia | `bot_data` e um dicionario — sem tipagem forte, erros so aparecem em runtime | Criar classe `BotContext` com atributos tipados |
| Handlers muito grandes | `callbacks.py` tem ~300 linhas com 12+ funcoes privadas no mesmo arquivo | Separar em `callbacks/navigation.py`, `callbacks/vocab.py`, `callbacks/actions.py` |
| Constantes magicas | MAX_HISTORY_TURNS, page_size=10, etc. espalhados | Criar `bot/constants.py` centralizado |
| Import relativo quebrando encapsulamento | `callbacks.py` faz `from bot.handlers.start import _get_welcome_text` — importa funcao privada de outro handler | Mover _get_welcome_text para utils ou tornar publica |
| GroqService._sync_generate | Roda em executor de threads — OK, mas sem timeout configurado | Adicionar timeout na chamada sync |
| Conversa 100% em memoria | Nivel do usuario, contexto, rate limit — tudo em RAM. Bot restart = perda total | Persistir nivel e rate limit no banco |

### 1.2 Estilo e Consistencia

**Pontos Fortes:**
- Nomenclatura consistente (snake_case para Python)
- Docstrings em todos os modulos
- Logging estruturado com logger por modulo
- Type hints na maioria das funcoes

**Oportunidades:**
| Item | Ocorrencias | Sugestao |
|------|-------------|----------|
| ~~~Optional typing~~ | `level: Optional[str] = None` vs `level: str \| None = None` | Padronizar para Python 3.10+ |
| ~~~Mensagens de erro~~ | Varias strings de fallback repetidas ("Sorry, I'm not ready yet...") | Criar constantes em `messages.py` |
| ~~~Parse mode repetido~~ | `parse_mode="Markdown"` em toda chamada | Configurar default no application ou criar helper |
| ~~~Tratamento de excecoes generico~~ | `except Exception as e:` em varios lugares | Usar excecoes especificas |

### 1.3 Dependencias e Pacotes

**requirements.txt** atual:
```
python-telegram-bot[job-queue]>=20.0
groq>=1.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
supabase>=2.0.0
```

**Avaliacao:** Limpo, minimalista, sem dependencias desnecessarias. Otimo para MVP.

**Sugestoes:**
- Nao ha pino de versoes especificas (so ranges) — pode quebrar com updates major
- `supabase` nao e usado em dev — poderia ser optional
- Faltam dev-dependencies: `pytest`, `pytest-asyncio`, `pytest-cov` (estao instaladas mas nao no requirements.txt)

---

## 2. Testes & Confiabilidade — Nota: A-

### 2.1 Estatisticas

| Metrica | Valor |
|---------|-------|
| Total de testes | 96 |
| Passando | 96 (100%) |
| Arquivos de teste | 7 |
| Cobertura estimada | ~70-80% (sem pytest-cov configurado) |
| Mocks | AsyncMock + MagicMock bem utilizados |
| Fixtures | Compartilhadas em conftest.py |

### 2.2 Cobertura por Modulo

| Modulo | Testes | Qualidade |
|--------|--------|-----------|
| `conversation.py` | 11 | Excelente — cobre todos os cenarios, edge cases |
| `rate_limiter.py` | 10 | Muito bom — multiplos usuarios, limites, persistencia |
| `formatting.py` | 16 | Excelente — extracao de vocab, paginacao, quebra de texto |
| `groq.py` | 11 | Excelente — retry, mensagens vazias, build de messages |
| `commands.py` | 6 | Bom, mas faltam mais cenarios de erro |
| `callbacks.py` | 10 | Bom, mas faltam testes para navegacao de nivel |
| `level_manager.py` | 18 | Excelente — cobre todos os metodos e edge cases |

### 2.3 Oportunidades de Melhoria

| Item | Problema | Sugestao |
|------|----------|----------|
| Testes de integracao | Nenhum teste que valide o fluxo completo (comando -> handler -> servico -> resposta) | Adicionar 2-3 testes end-to-end mockados |
| Testes do webhook_server | zero | Adicionar testes para /health e /webhook |
| Cobertura de erro | Nao testa cenarios como `database.py` corrompido, config invalida | Adicionar testes de configuracao |
| Testes de message.py | Testes de extracao de vocab existem, mas nao do handler completo | Adicionar teste de `handle_message` com fluxo completo |
| Fixtures com configured_context | Mock_db, mock_groq, etc. padronizados — mas nao incluem level_manager | Adicionar `mock_level_manager` a fixture |
| pytest-cov | Nao configurado | Adicionar ao requirements.txt e configurar |

### 2.4 Pontos Fortes nos Testes

- Uso consistente de AsyncMock para metodos async
- Fixtures compartilhadas e reutilizaveis
- `sample_vocab_entries` fixture bem construida
- Testes de paginacao e topicos aleatorios (com verificacao estatistica)
- `test_topic_different_each_time` — excelente teste de randomicidade

---

## 3. UX do Bot — Nota: B+

### 3.1 Fluxo do Usuario

```
/start
  └─> Boas-vindas + escolha de nivel (A1/A2/B1)
       └─> Menu principal
            ├─ [Start a Conversation] -> Sugestao de topico
            ├─ [How it Works] -> Explicacao
            ├─ [My Vocabulary] -> Lista paginada
            └─ [Practice Topics] -> Sugestao de topico

Conversa livre:
  Usuario envia texto
    └─> Bot responde + [More Examples] [Explain Word] [Practice This]

Comandos:
  /level -> Ver/trocar nivel
  /reset -> Limpar historico
  /topic -> Sugerir topico
  /vocab -> Ver vocabulario
  /help  -> Ajuda
```

### 3.2 Avaliacao

**Pontos Fortes:**
- Botoes inline bem desenhados com emojis e labels claros
- Indicador de digitacao ("typing...") enquanto processa
- Rate limiter amigavel (soft limit com aviso, nunca bloqueia)
- Vocabulario persistente com paginacao
- 15 topicos variados para praticar
- Correcoes via LLM sao contextualizadas e gentis
- Fallbacks elegantes quando LLM falha

**Oportunidades de Melhoria:**

| Item | Problema | Sugestao |
|------|----------|----------|
| ~~~Feedback de carregamento~~ | So mostra "typing..." — sem indicacao de progresso | Adicionar mensagem "Thinking..." com edicao posterior |
| ~~~/vocab sem filtro de nivel~~ | Filtra por nivel, mas nao mostra qual nivel esta sendo exibido | Incluir "[A1]" no titulo do vocabulario |
| ~~~Nivel reset ao restart~~ | Nivel e em memoria — se o bot reiniciar, volta pra A1 sem aviso | Avisar /level no /start se nivel foi perdido |
| ~~~Sem confirmacao de acao~~ | Botoes "More Examples", etc. nao tem confirmacao visual | Mostrar "Generating..." antes do resultado |
| ~~~Comandos nao tem descricao no menu~~ | /start mostra botoes, mas usuario nao sabe que existe /level, /reset | Adicionar "Commands" ao menu principal |
| ~~~Erro generico "not ready"~~ | Mensagem de servico nao inicializado aparece em varios lugares | Ser mais especifico ou tentar reinicializar |
| ~~~Sem onboarding alem do /start~~ | Usuario pode se sentir perdido apos escolher nivel | Mini-tutorial de 3 passos apos escolha inicial |

### 3.3 Comparacao com Spec Original

| Funcionalidade (spec-english-teacher-bot.md) | Status | Observacao |
|----------------------------------------------|--------|------------|
| Comandos /start, /help, /reset, /vocab, /topic | ✅ Completo | |
| Conversa livre com LLM | ✅ Completo | |
| Correcoes contextuais | ✅ Completo | |
| Botoes More Examples, Explain Word, Practice This | ✅ Completo | |
| Vocabulario persistente (SQLite/Supabase) | ✅ Completo | |
| Rate limiter (100 msg/dia) | ✅ Completo | |
| 15 topicos fixos | ✅ Completo | |
| Niveis adaptativos A1/A2/B1 | ✅ Completo | Adicionado apos spec inicial |
| Webhook + FastAPI para Render | ✅ Completo | |
| Audio (STT/TTS) | ❌ Nao implementado | Pos-MVP no spec |
| Flashcards / revisao | ❌ Nao implementado | Consideracao futura |
| Estatisticas de progresso | ❌ Nao implementado | Consideracao futura |
| Suporte a imagens | ❌ Nao implementado | Consideracao futura |

---

## 4. Prontidao para Producao — Nota: C+

### 4.1 Deploy e Infraestrutura

**Setup Atual:**
- Render Web Service com FastAPI + Uvicorn
- Webhook registrado automaticamente no startup
- Health check em /health
- Procfile + runtime.txt configurados

**Riscos Identificados:**

| Risco | Impacto | Probabilidade | Mitigacao |
|-------|---------|---------------|-----------|
| Estado em memoria (conversa, nivel, rate limit) se perde no restart | Alto — usuario perde conversa e nivel | Alta (todo deploy) | Persistir nivel e rate limit no banco |
| Render free tier pode ter cold start (15s+) | Medio — usuario espera | Media | Adicionar warmup/configurar keep-alive |
| Nenhum logging estruturado | Medio — dificil debugar em prod | Media | Adicionar logging com rotação e niveis |
| Sem monitoramento de erros | Alto — bugs silenciosos | Media | Integrar Sentry ou similar (gratuito) |
| Rate limiter sem bloqueio real | Baixo — soft limit pode ser ignorado | Baixa | Manter como esta (soft limit e intencional) |
| Groq API key exposta em logs | Alto — vazamento de chave | Baixa (se logs nao sao expostos) | Revisar logging para nunca logar chaves |
| Sem testes de carga | Medio — nao sabe limite do free tier | Media | Testar com script simples |

### 4.2 Seguranca

**Pontos Fortes:**
- Chaves em variaveis de ambiente (.env + Render env vars)
- .gitignore adequado (exclui .env, *.db, __pycache__)
- Tratamento de erros nao vaza informacoes internas

**Oportunidades:**
- Mensagens do usuario nao sao sanitizadas — podem conter markup malicioso
- Nao ha validacao de que o webhook request veio do Telegram (falta verificacao de HMAC)
- Comando `/reset` nao requer confirmacao — pode apagar historico acidentalmente
- `webhook_server.py` nao valida o token do webhook

### 4.3 Tratamento de Erros

**Cenarios Cobertos:**

| Erro | Tratamento |
|------|------------|
| LLM timeout | Retry 2x com backoff de 2s, depois fallback |
| LLM retorna vazio/None | Mensagem amigavel |
| DB erro de escrita | Loga erro, continua conversa |
| Comando desconhecido | Callback "didn't understand" |
| Servico nao inicializado | Mensagem "not ready yet" |

**Lacunas:**

| Cenario | Problema |
|---------|----------|
| Telegram API rate limit | Nao tratado — pode resultar em 429 |
| Webhook request mal formatado | Loga erro mas retorna 500 sem detalhes |
| Configuracao invalida em runtime | Sendo validada em load_config(), mas apenas se chamar |
| Concurrent access ao bot_data | Dicionario nao e thread-safe |
| DB connection leak (SQLite) | Conexoes sao fechadas em finally — OK, mas poderia usar context manager |

---

## 5. Sugestoes Prioritarias (Top 10)

### Criticos (Fazer imediatamente)

| # | Sugestao | Esforco | Impacto | Dimensao |
|---|----------|---------|---------|----------|
| 1 | **Persistir nivel do usuario no banco de dados** | Medio | Alto — nivel e essencial e se perde no restart | Arquitetura |
| 2 | **Adicionar logging estruturado com rotacao** | Baixo | Alto — sem logs, producao e cega | Producao |
| 3 | **Validar webhook requests (HMAC)** | Baixo | Alto — seguranca do webhook | Seguranca |

### Importantes (Proxima sprint)

| # | Sugestao | Esforco | Impacto | Dimensao |
|---|----------|---------|---------|----------|
| 4 | **Separar callbacks.py em modulos menores** | Medio | Medio — manutencao futura | Codigo |
| 5 | **Centralizar constantes e mensagens** | Baixo | Medio — DRY e consistencia | Codigo |
| 6 | **Adicionar onboarding tutorial pos-/start** | Medio | Medio — melhora primeira experiencia | UX |
| 7 | **Adicionar pytest-cov e monitorar cobertura** | Baixo | Medio — visibilidade de qualidade | Testes |

### Desejaveis (Proximas semanas)

| # | Sugestao | Esforco | Impacto | Dimensao |
|---|----------|---------|---------|----------|
| 8 | **Implementar audio (Deepgram + ElevenLabs)** | Alto | Alto — feature mais pedida | Funcionalidade |
| 9 | **Criar modulo de estatisticas de progresso** | Alto | Alto — engajamento do usuario | Funcionalidade |
| 10 | **Refinar correcoes do LLM (prompt engineering)** | Medio | Alto — qualidade percebida | Funcionalidade |

---

## 6. Roteiro Sugerido de Melhorias

```
Sprint 1 (Fundacao)
├─> Persistir nivel no banco de dados
├─> Logging estruturado (Sentry ou file rotation)
├─> Validacao HMAC no webhook
└─> pytest-cov + CI basico (GitHub Actions)

Sprint 2 (Qualidade de Codigo)
├─> Separar callbacks.py em modulos
├─> Criar bot/constants.py + bot/messages.py
├─> Adicionar testes de integracao (3-5 fluxos completos)
├─> Refatorar bot_data -> BotContext tipado

Sprint 3 (UX)
├─> Onboarding tutorial pos-/start
├─> Melhorar feedback de carregamento
├─> Adicionar /stats (basico: palavras aprendidas, dias)
└─> Indicar nivel atual na UI do vocabulario

Sprint 4 (Features)
├─> STT com Deepgram (entrada de audio)
├─> TTS com ElevenLabs (saida de audio)
├─> Correcoes mais inteligentes (prompt tuning)
└─> Modo conversa guiada (licoes passo a passo)
```

---

## 7. Matriz de Decisoes Tecnicas (Registro)

| # | Decisao Atual | Problema Identificado | Alternativa Recomendada |
|---|---------------|----------------------|------------------------|
| 1 | Estado em memoria para nivel | Perde ao restart | Salvar `user_level` no banco (coluna `users` ou tabela separada) |
| 2 | Log basico com print+logging | Sem rotacao, sem nivelacao | logging.handlers.RotatingFileHandler + Sentry SDK |
| 3 | bot_data como dicionario | Sem tipagem, erros silenciosos | Classe `BotContext(Pydantic)` ou TypedDict |
| 4 | Handlers em arquivos unicos | callbacks.py com ~300 linhas | Separar por dominio (navigation, vocab, actions) |
| 5 | Sem testes de webhook | Cobertura cega para producao | TestClient do FastAPI + mock do Application |
| 6 | requirements.txt sem versoes fixas | Risco de breaking changes | Usar `>=X.Y,<X+1.0` ou poetry.lock |
| 7 | Dependencias de teste ausentes do requirements.txt | Setup em novo ambiente falha | Separar dev-requirements.txt ou usar extras |

---

## 8. Checklist de Acao Imediata

- [ ] **Persistir nivel** — Adicionar coluna `user_level` ou tabela separada, migrar LevelManager para usar banco
- [ ] **Adicionar logging rotativo** — Configurar RotatingFileHandler, definir niveis por modulo
- [ ] **HMAC no webhook** — Validar que requests ao /webhook vieram do Telegram
- [ ] **pytest-cov** — Adicionar ao projeto, configurar .coveragerc
- [ ] **Separar callbacks.py** — Criar subpacote bot/handlers/callbacks/
- [ ] **Centralizar constantes** — Criar bot/constants.py com page_size, max_history, etc.
- [ ] **Testes de integracao** — 3-5 testes de fluxo completo (start -> conversa -> vocab)
- [ ] **GitHub Actions CI** — Rodar pytest a cada push

---

## 9. Glossario da Avaliacao

| Termo | Significado |
|-------|-------------|
| **Nota A** | Excelente — pronto sem reservas |
| **Nota B** | Bom — funcional, com oportunidades de melhoria |
| **Nota C** | Regular — funciona mas tem riscos ou lacunas |
| **MVP** | Produto viavel minimo — funcionalidades essenciais |
| **DRY** | Don't Repeat Yourself — principio de evitar duplicacao |
| **HMAC** | Hash-based Message Authentication Code — validacao de origem |
| **Cold Start** | Tempo ate o servidor responder apos periodo inativo |
| **Spin Down** | Render desliga o servico apos 15min sem trafego |

---

## 10. Proximos Passos

1. **Revisar este spec** — Validar se as prioridades estao corretas para voce
2. **Escolher os 3 itens do topo** para implementar na Sprint 1
3. **Decidir qual feature inacabada** atacar primeiro: Audio ou Estatisticas
4. **Refinar os specs** com base nesta avaliacao

---

*Fim do documento de avaliacao.*
