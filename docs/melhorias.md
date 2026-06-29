# Melhorias e Funcionalidades — Jarvis/LinguaBot

> Análise do projeto em `C:\web-projects\jarvis` em 28/06/2026.

---

## 1. Arquitetura e Qualidade de Código

| # | Melhoria | Impacto | Esforço |
|---|----------|---------|---------|
| 1.1 | **Tipagem moderna**: migrar de `Optional[str]` para `str \| None` em todos os arquivos | Média | Baixo |
| 1.2 | **Arquivo de constantes centralizado** (`bot/constants.py`): unificar speed options, defaults, limites de taxa, e configurações de TTS espalhados por `keyboards.py`, `config.py` e handlers | Alta | Baixo |
| 1.3 | **Módulo de typing próprio** (`bot/typing.py`): type aliases para `UserLevel`, `VoiceOption`, `SpeedOption`, etc. | Média | Baixo |
| 1.4 | **Persistência de conversação**: salvar `ConversationManager` no banco (SQLite/Supabase) opcionalmente para não perder histórico em restart | Média | Médio |
| 1.5 | **Lock no rate limiter**: adicionar `threading.Lock` ou `asyncio.Lock` no acesso ao JSON para evitar corrupção em concorrência | Baixa | Baixo |
| 1.6 | **Consistência async no LevelManager**: tornar `set_level()` async para alinhar com `persist_level()` (remover TODO documentado) | Baixa | Baixo |
| 1.7 | **Separar responsabilidades do `callbacks.py`** (761 linhas): extrair lógica de negócio para services, deixando apenas roteamento no handler | Alta | Médio |
| 1.8 | **Adicionar `from __future__ import annotations`** em todos os arquivos para habilitar avaliação postergada de tipos | Média | Baixo |
| 1.9 | **Logging estruturado**: substituir `print()` e logs soltos por `structlog` ou logging formatado com níveis consistentes | Média | Médio |

---

## 2. Funcionalidades Novas

| # | Funcionalidade | Descrição | Prioridade |
|---|---------------|-----------|------------|
| 2.1 | **Detecção automática de nível** | Analisar erros gramaticais e lexicais do usuário ao longo da conversa e sugerir promoção (A1→A2→B1) ou rebaixamento automático via inline button | Alta |
| 2.2 | **Progress tracking** | Estatísticas por usuário: palavras aprendidas, erros comuns, tempo de estudo, tópicos mais praticados. Comando `/stats` e dashboard visual | Alta |
| 2.3 | **Sistema de repetição espaçada (SRS)** | Revisão programada de vocabulário com algoritmo similar a Anki/SM-2. O bot envia revisões periodicamente ou sob demanda com `/review` | Alta |
| 2.4 | **Níveis B2 e C1** | Expandir system prompts para níveis avançados, com vocabulário acadêmico, expressões idiomáticas e estruturas complexas | Média |
| 2.5 | **Botão "Ouvir Novamente"** | Reproduzir o último áudio TTS gerado sem precisar reenviar a mensagem | Média |
| 2.6 | **Modo texto-only** | Toggle para desabilitar TTS e economizar caracteres da API Deepgram. Útil para usuários com conexão lenta | Média |
| 2.7 | **Áudio nos callbacks** | Gerar TTS também para "More Examples", "Explain This Word" e "Practice This" (atualmente só texto) | Média |
| 2.8 | **Exportar vocabulário** | Comando `/export csv` ou `/export json` para baixar a lista de palavras aprendidas | Baixa |
| 2.9 | **Sessões temáticas intensivas** | Modo "prática intensiva" em um único tópico por N turnos, com correções aprofundadas | Baixa |
| 2.10 | **Modo conversa livre vs. modo lição** | Alternar entre conversa natural (atual) e modo estruturado com exercícios gramaticais | Baixa |
| 2.11 | **Correção seletiva** | Permitir que o usuário peça correção de uma frase específica com um botão, ao invés de correção automática sempre | Baixa |
| 2.12 | **Suporte a imagem** | Enviar uma imagem e o bot descrevê-la em inglês no nível do usuário (LLM multimodal com Groq LLaVA ou similar) | Média |

---

## 3. Testes

| # | Melhoria | Estado Atual |
|---|----------|--------------|
| 3.1 | **Testes para `message.py`** (MessageHandler de texto) | ❌ Inexistente |
| 3.2 | **Testes para `test_callbacks.py`** — cobrir todos os callbacks (More Examples, Explain, Practice, configurações) | ⚠️ Parcial |
| 3.3 | **Testes de integração** com Groq/Deepgram reais (com mock de rede via `responses` ou `httpx_mock`) | ❌ Inexistente |
| 3.4 | **Testes para o webhook server** (FastAPI: `/health`, `/webhook`) | ❌ Inexistente |
| 3.5 | **Testes para `database.py`** (ambas implementações SQLite e Supabase) | ❌ Inexistente |
| 3.6 | **Testes para `rate_limiter.py`** (já existe, verificar cobertura de concorrência) | ⚠️ Parcial |
| 3.7 | **Fixture compartilhada** para criar um `Application` falso do PTB e reduzir boilerplate nos testes | Média |
| 3.8 | **Cobertura mínima (pytest-cov)**: configurar threshold de 80% | Média |

---

## 4. DevOps e Infraestrutura

| # | Melhoria | Justificativa |
|---|----------|---------------|
| 4.1 | **Dockerfile multi-estágio** | Ambiente reprodutível local e em produção; facilita testes em CI |
| 4.2 | **CI/CD com GitHub Actions** | Rodar `ruff check`, `mypy`, `pytest` a cada push/PR |
| 4.3 | **Pre-commit hooks** | `ruff`, `mypy`, `pytest` automáticos antes de cada commit |
| 4.4 | **`.python-version`** | Facilitar gerenciamento de versão com pyenv |
| 4.5 | **Separar `.env` rastreado do `.env.example`** | Garantir que chaves reais nunca sejam commitadas (adicionar `.env` ao `.gitignore` já existe, mas verificar se há arquivos sensíveis no staging) |
| 4.6 | **Health check melhorado** | Endpoint `/health` com métricas: latência do Groq, cache hit ratio, uptime, versão do bot |
| 4.7 | **Grafana/Prometheus ou métricas leves** | Monitorar uso da API Deepgram/Groq, custos, erros |
| 4.8 | **Configuração de ambiente (dev/staging/prod)** | Separar `.env.development`, `.env.staging`, `.env.production` com validação |
| 4.9 | **Deploy automatizado via Render API ou GH Actions** | Trigger automático ao fazer merge na main |

---

## 5. Documentação

| # | Melhoria | Descrição |
|---|----------|-----------|
| 5.1 | **Diagrama de arquitetura** (Mermaid) | Adicionar no README.md um diagrama visual do fluxo de dados |
| 5.2 | **Comentários e docstrings em inglês** | Consistência internacional; facilita contribuição de devs não-PT |
| 5.3 | **ADR (Architecture Decision Records)** | Documentar decisões importantes (ex: "por que Deepgram virou TTS primário e não ElevenLabs") |
| 5.4 | **CHANGELOG.md** | Manter registro de versões com base em tags git |
| 5.5 | **CONTRIBUTING.md** | Guia de como contribuir: setup, estilo de código, fluxo de PR |
| 5.6 | **Swagger/OpenAPI** | Documentar automaticamente os endpoints FastAPI (já vem com FastAPI via `/docs`) |

---

## 6. Observações Técnicas

- **Python 3.14.3** em `runtime.txt` é extremamente recente (pré-release). Verificar compatibilidade de todas as dependências (algumas podem não ter wheel publicado). Alternativa segura: 3.12.x ou 3.13.x.
- **Atualmente com 100+ testes**, mas sem cobertura nos handlers principais (`message.py`). Prioridade alta.
- **O arquivo `callbacks.py` com 761 linhas** é o maior gargalo de manutenção — refatoração prioritária.
- **Conversation history 100% em RAM** significa perda de contexto em restart do servidor Render (que ocorre periodicamente no free tier).
