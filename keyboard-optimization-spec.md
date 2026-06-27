# Spec: Keyboard Optimization — Botões com Expandir/Recolher

> **Versao:** 1.0
> **Data:** 27 de Junho de 2026
> **Tipo:** Spec de Funcionalidade — UX de Botoes Inline
> **Projeto:** LinguaBot — English Teacher Telegram Bot

---

## 1. Resumo

Otimizar os botoes inline do LinguaBot para evitar poluicao visual durante a conversa. Em vez de mostrar varios botoes fixos apos cada mensagem, apenas **um botao principal** sera exibido. Ao clicar nele, os demais botoes aparecem. Um dos botoes expandidos serve para ocultar novamente.

---

## 2. Situacao Atual

### 2.1 Botoes de Conversa (`conversation_buttons`)
Apos cada resposta do bot, **3 botoes** aparecem fixos:
```
[📝 More Examples]  [📖 Explain This Word]
[🎯 Practice This]
```

### 2.2 Menu Principal (`main_menu`)
No /start e ao voltar ao menu:
```
[💬 Start a Conversation]  [❓ How it Works]
[📚 My Vocabulary]          [🎯 Practice Topics]
```

### 2.3 Paginacao de Vocabulario (`vocab_pagination`)
Na tela de vocabulario:
```
[◀️ Previous]  [Next ▶️]
[🔙 Back to Menu]
```

### 2.4 Menu de Topicoss (`topics_menu`)
Ao escolher um topico:
```
[👋 Greetings]  [🍔 Food & Drinks]
[👨‍👩‍👧‍👦 Family]  [🌤️ Weather]
[📅 Daily Routine]
[🎲 Random Topic]
[🔙 Back to Menu]
```

### 2.5 Telas SEM compressao (mantidas visiveis)

| Tela | Botoes | Motivo |
|------|--------|--------|
| **Selecao de nivel** (`level_selection_keyboard`) | A1, A2, B1 | Acao unica e rapida |
| **Sugestao de topico** (`topic_suggestion`) | Yes, let's talk!, Another Topic, Back | Decisao rapida do usuario |

---

## 3. Novo Comportamento Geral

### 3.1 Conceito

1. **Estado comprimido (padrao):** Apenas 1 botao e exibido: `➕ More Options`
2. **Ao clicar em + More Options:** O botao e substituido pelos botoes reais + um botao de fechar
3. **Ao clicar em ◀ Hide Options:** Os botoes reais sao substituidos de volta para `➕ More Options`
4. **A cada nova mensagem do usuario:** A resposta do bot volta ao estado comprimido
5. **Apos clicar em um botao de acao** (More Examples, Explain Word, etc.): A resposta ja vem **expandida**

### 3.2 Fluxo de Transicao

```
Estado comprimido:
[➕ More Options]
        |
        v (clica em + More Options)
Estado expandido:
[📝 More Examples]  [📖 Explain This Word]
[🎯 Practice This]
[◀ Hide Options]
        |
        v (clica em Hide Options ou envia nova mensagem)
Estado comprimido:
[➕ More Options]
```

### 3.3 Mecanismo de Exibicao

- **Inline editing:** Usar `edit_message_text()` ou `edit_message_reply_markup()` do Telegram para alterar apenas os botoes, mantendo o texto da mensagem.
- **Fileira propria:** O botao `➕ More Options` ocupa uma linha inteira propria, separado do texto.
- **Botao de fechar:** O botao `◀ Hide Options` fica sempre na **ultima linha** do estado expandido.

---

## 4. Detalhamento por Tela

### 4.1 Botoes de Conversa (`conversation_buttons`)

**Comprimido:**
```
[➕ More Options]
```

**Expandido:**
```
[📝 More Examples]  [📖 Explain This Word]
[🎯 Practice This]
[◀ Hide Options]
```

**Callback data:**
| Botao | callback_data | Acao |
|-------|--------------|------|
| + More Options | `show_more_options` | Substitui pelo estado expandido |
| ◀ Hide Options | `hide_options` | Substitui pelo estado comprimido |
| More Examples | `more_examples` | Gera exemplos + resposta expandida |
| Explain This Word | `explain_word` | Explica palavra + resposta expandida |
| Practice This | `practice_this` | Gera exercicio + resposta expandida |

### 4.2 Menu Principal (`main_menu`)

**Comprimido:**
```
[➕ More Options]
```

**Expandido:**
```
[💬 Start a Conversation]  [❓ How it Works]
[📚 My Vocabulary]          [🎯 Practice Topics]
[◀ Hide Options]
```

### 4.3 Paginacao de Vocabulario (`vocab_pagination`)

**Estado atual (visivel):**
```
[◀️ Previous]  [Next ▶️]
[🔙 Back to Menu]
```

**Comprimido:**
```
[➕ More Options]
```

**Expandido (com paginacao):**
```
[◀️ Previous]  [Next ▶️]
[🔙 Back to Menu]
[◀ Hide Options]
```

**Excecao:** Se so houver 1 pagina (sem Previous/Next), o botao `➕ More Options` leva direto para:
```
[🔙 Back to Menu]
[◀ Hide Options]
```

### 4.4 Menu de Topicoss (`topics_menu`)

**Comprimido:**
```
[➕ More Options]
```

**Expandido:**
```
[👋 Greetings]  [🍔 Food & Drinks]
[👨‍👩‍👧‍👦 Family]  [🌤️ Weather]
[📅 Daily Routine]
[🎲 Random Topic]
[🔙 Back to Menu]
[◀ Hide Options]
```

### 4.5 `back_to_menu_button` (botao unico)

**Comprimido (mantido como esta):**
```
[🔙 Back to Menu]
```

Nao precisa de compressao — ja e um unico botao.

### 4.6 Telas SEM compressao (visiveis sempre)

| Tela | Layout | Callback data |
|------|--------|---------------|
| **level_selection_keyboard** | A1, A2, B1 (sempre visiveis) | `set_level_A1`, `set_level_A2`, `set_level_B1` |
| **topic_suggestion** | [Yes, let's talk!] [Another Topic] [Back to Menu] | `start_topic_{topic}`, `show_topics`, `back_to_menu` |

---

## 5. Comportamento Apos Acoes

### 5.1 Usuario clica em "+ More Options"

O botao e substituido pelos botoes reais + "◀ Hide Options".
- Metodo: `edit_message_reply_markup()` — apenas altera os botoes, sem alterar o texto.
- **Feedback visual:** Antes de expandir, mostra brevemente "🔄 Loading..." por ~0.5s via `edit_message_text()`, depois troca para os botoes expandidos.
- O callback `show_more_options` faz: `query.answer()` -> mostra loading -> troca reply_markup.

### 5.2 Usuario clica em "◀ Hide Options"

Os botoes reais sao substituidos de volta por "+ More Options".
- Metodo: `edit_message_reply_markup()` — apenas altera os botoes.
- O callback `hide_options` apenas responde com `query.answer()` e troca o reply_markup.

### 5.3 Usuario clica em um botao de acao (More Examples, Explain Word, Practice This)

A resposta do Groq vem **expandida** (com todos os botoes + Hide Options).
- Metodo: `edit_message_text()` com o texto da resposta + reply_markup expandido.
- Excecao: Se o resultado for erro, mostra botoes comprimidos.

### 5.4 Usuario envia nova mensagem de texto

A nova resposta do bot sempre vem **comprimida** (so "+ More Options").
- O estado expandido anterior e substituido pelo novo estado comprimido.

### 5.5 Navegacao entre telas (ex: vai para vocabulario, volta ao menu)

Ao mudar de tela, o estado padrao depende do tipo de navegacao:
- **Navegacao entre telas diferentes** (menu -> conversa, menu -> vocabulario): estado **comprimido**.
- **Navegacao dentro da mesma tela** (vocabulario: pagina 1 -> pagina 2): estado **expandido** (mantem botoes visiveis).
- Excecao: telas sem compressao (nivel, topico) mantem-se visiveis sempre.

**Resumo:**
- `vocab_page_{n}` — resposta vem expandida (mantem navegacao visivel)
- Demais transicoes (menu, conversa, topicos) — estado comprimido

---

## 6. Modificacoes no Codigo

### 6.1 Arquivos a Modificar

| Arquivo | Mudanca |
|---------|---------|
| `bot/utils/keyboards.py` | Criar funcao `collapse_keyboard()`; modificar `conversation_buttons()`, `main_menu()`, `vocab_pagination()`, `topics_menu()` para aceitar parametro boolean `expanded=False` |
| `bot/handlers/callbacks.py` | Adicionar handlers para `show_more_options` e `hide_options`; modificar fluxo existente para retornar estado comprimido/expandido conforme necessario |
| `bot/handlers/message.py` | Garantir que `handle_message` sempre use estado comprimido |
| `bot/handlers/commands.py` | Garantir que `/reset`, `/vocab`, `/topic` usem estado comprimido |
| `bot/handlers/start.py` | Garantir que `/start` use estado comprimido |

### 6.2 Arquivos NOVOS

Nenhum. A funcionalidade e puramente modificacao dos arquivos existentes.

### 6.3 Funcao Auxiliar Sugerida: `collapse_keyboard`

```python
def collapse_keyboard(expanded_keyboard: list[list], expanded: bool = False) -> InlineKeyboardMarkup:
    """Encapsula um teclado inline com comportamento de expandir/recolher.

    Args:
        expanded_keyboard: O teclado completo (todos os botoes).
        expanded: Se True, mostra todos os botoes + Hide Options.
                  Se False, mostra apenas "+ More Options".

    Returns:
        InlineKeyboardMarkup com o estado apropriado.
    """
    if expanded:
        keyboard = list(expanded_keyboard)  # copia
        keyboard.append([InlineKeyboardButton("◀ Hide Options", callback_data="hide_options")])
        return InlineKeyboardMarkup(keyboard)

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ More Options", callback_data="show_more_options")],
    ])
```

### 6.4 Fluxo de Callbacks

Novos callbacks a adicionar em `handle_callback()`:

```python
elif data == "show_more_options":
    await _expand_options(query, context)

elif data == "hide_options":
    await _collapse_options(query, context)
```

Funcoes auxiliares:

```python
async def _expand_options(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Expande os botoes: substitui '+ More Options' pelos botoes reais."""
    # O estado expandido e determinado pelo tipo de mensagem atual
    # Precisamos saber qual teclado estava ativo.
    # Estrategia: armazenar no context.user_data qual o 'tipo' de tela atual
    # (conversa, menu, vocab, topicos)
    await query.answer()

    # Recupera o tipo de tela salvo no user_data
    screen_type = context.user_data.get("screen_type", "conversation")
    expanded_keyboard = _get_keyboard_for_screen(screen_type, expanded=True)

    await query.edit_message_reply_markup(reply_markup=expanded_keyboard)


async def _collapse_options(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recolhe os botoes: substitui botoes por '+ More Options'."""
    await query.answer()

    collapsed_keyboard = _get_collapsed_keyboard()
    await query.edit_message_reply_markup(reply_markup=collapsed_keyboard)


def _get_keyboard_for_screen(screen_type: str, expanded: bool = False) -> InlineKeyboardMarkup:
    """Retorna o teclado apropriado para cada tela, comprimido ou expandido."""
    keyboards = {
        "conversation": conversation_buttons,
        "menu": main_menu,
        "vocab": lambda: vocab_pagination(page=context.user_data.get("page", 1), total_pages=context.user_data.get("total_pages", 1)),
        "topics": topics_menu,
    }
    key_func = keyboards.get(screen_type, conversation_buttons)
    full_keyboard = key_func()
    # Encapsula com collapse/expand
    return collapse_keyboard(full_keyboard.inline_keyboard, expanded=expanded)
```

### 6.5 Rastreamento de Tela Atual

Para que `_expand_options` saiba qual teclado expandir, precisamos armazenar o **tipo de tela** em `context.user_data` sempre que uma tela for exibida:

```python
# Exemplo: ao mostrar vocabulario
context.user_data["screen_type"] = "vocab"
context.user_data["page"] = current_page
context.user_data["total_pages"] = total_pages
```

| screen_type | Teclado |
|-------------|---------|
| `conversation` | `conversation_buttons()` |
| `menu` | `main_menu()` |
| `vocab` | `vocab_pagination(page, total_pages)` |
| `topics` | `topics_menu()` |

---

## 7. Callbacks Data — Tabela Completa

| callback_data | Handler | Descricao |
|--------------|---------|-----------|
| `show_more_options` | `_expand_options` | Expande botoes (comprimido -> expandido) |
| `hide_options` | `_collapse_options` | Recolhe botoes (expandido -> comprimido) |
| `back_to_menu` | `_show_menu` | Volta ao menu principal (comprimido) |
| `how_it_works` | `_show_how_it_works` | Mostra tutorial (comprimido) |
| `start_conversation` | `_start_conversation` | Inicia conversa (comprimido) |
| `show_vocab` | `_show_vocab` | Mostra vocabulario (comprimido) |
| `show_topics` | `_show_topics` | Sugere topico (comprimido) |
| `more_examples` | `_more_examples` | Gera exemplos (expandido) |
| `explain_word` | `_explain_word` | Explica palavra (expandido) |
| `practice_this` | `_practice_this` | Gera exercicio (expandido) |
| `vocab_page_{n}` | `_show_vocab_page` | Pagina de vocab (expandido — usuario esta navegando) |
| `start_topic_{t}` | `_start_topic` | Inicia topico (expandido) |
| `set_level_{l}` | `_set_level` | Define nivel (mantem visivel) |

---

## 8. Telas SEM Compressao (Sempre Visiveis)

### 8.1 Selecao de Nivel (`level_selection_keyboard`)

Nao se aplica compressao. Os 3 botoes ficam sempre visiveis:
```
[A1 - Iniciante]
[A2 - Básico]
[B1 - Intermediário]
```

### 8.2 Sugestao de Topico (`topic_suggestion`)

Nao se aplica compressao. Os botoes ficam sempre visiveis:
```
[✅ Yes, let's talk!]  [🔄 Another Topic]
[🔙 Back to Menu]
```

---

## 9. Fluxos de Usuario (Exemplos)

### 9.1 Fluxo Normal de Conversa

```
Usuario: "Hello!"
Bot: "Hi there! How are you today?"
     [➕ More Options]

Usuario: "I'm fine, thanks!"
Bot: "That's great to hear! What did you do today?"
     [➕ More Options]

Usuario clica: + More Options
Bot: (edita mensagem)
     "That's great to hear! What did you do today?"
     [📝 More Examples]  [📖 Explain This Word]
     [🎯 Practice This]
     [◀ Hide Options]

Usuario clica: More Examples
Bot: "Sure! Here are some examples..."
     [📝 More Examples]  [📖 Explain This Word]
     [🎯 Practice This]
     [◀ Hide Options]

Usuario clica: Hide Options
Bot: (edita mensagem)
     "Sure! Here are some examples..."
     [➕ More Options]

Usuario: "I went to the park"
Bot: "Nice! I went to the park too last week..."
     [➕ More Options]  ← sempre volta a comprimido apos nova msg
```

### 9.2 Fluxo de Menu

```
Usuario: /start
Bot: "Hello! I'm LinguaBot..."
     [➕ More Options]

Usuario clica: + More Options
Bot: (edita)
     [💬 Start a Conversation]  [❓ How it Works]
     [📚 My Vocabulary]          [🎯 Practice Topics]
     [◀ Hide Options]

Usuario clica: My Vocabulary
Bot: "📚 Your Vocabulary (5 words)..."
     [➕ More Options]

Usuario clica: + More Options
Bot: (edita)
     [◀️ Previous]  [Next ▶️]
     [🔙 Back to Menu]
     [◀ Hide Options]
```

---

## 10. Edge Cases e Decisoes

### 10.1 Telefone estreito / Layout

O Telegram ja quebra botoes inline em linhas conforme a largura da tela. O layout proposto usa 2 botoes por linha como maximo, o que funciona bem em todos os tamanhos de tela.

### 10.2 Estado de tela perdido

Se o bot reiniciar, `context.user_data` e perdido (in-memory). Nesse caso:
- O `screen_type` padrao deve ser `conversation`
- `_expand_options` deve ter um fallback seguro

**Solucao:** No handler de `show_more_options`, se `screen_type` nao estiver definido, usar `conversation` como fallback.

### 10.3 Multiplas mensagens abertas

Se o usuario tiver varias mensagens do bot abertas com botoes, cada uma tem seu proprio estado (comprimido ou expandido). Isso e natural do Telegram — cada mensagem e independente.

### 10.4 Botoes de nivel e topico misturados

As telas de nivel e topico aparecem APENAS em contextos especificos:
- Nivel: via `/level` ou no primeiro `/start`
- Topico: apos clicar em "Start a Conversation" ou `/topic`

Nestas telas, nao ha compressao — os botoes aparecem sempre visiveis.

---

## 11. Implementacao Sugerida

### Fase 1 — Base (prioridade maxima)

1. Criar funcao `collapse_keyboard()` em `keyboards.py`
2. Adicionar callbacks `show_more_options` e `hide_options` em `callbacks.py`
3. Modificar `main_menu()` e `conversation_buttons()` para aceitar estado comprimido
4. Atualizar `handle_message` para usar estado comprimido
5. Adicionar rastreamento de `screen_type` no `user_data`

### Fase 2 — Demais telas

6. Modificar `vocab_pagination()` para compressao
7. Modificar `topics_menu()` para compressao
8. Garantir que telas sem compressao (nivel, topico) mantenham-se visiveis

### Fase 3 — Testes

9. Atualizar testes existentes para refletir novo layout de botoes
10. Testar fluxos: comprimido -> expandido -> acao -> comprimido
11. Testar fallback se `screen_type` nao definido

---

## 12. Registro de Decisoes

| # | Decisao | Alternativa | Motivo |
|---|---------|-------------|--------|
| 1 | `+ More Options` em fileira propria | Junto ao texto | Clareza visual |
| 2 | Estado comprimido como padrao | Expandido como padrao | Minimizar poluicao visual |
| 3 | Resposta de acao vem expandida | Resposta de acao vem comprimida | Usuario ja esta interagindo, manter continuidade |
| 4 | Nova msg do usuario volta ao comprimido | Mantem estado anterior | Consistencia — cada turno comeca limpo |
| 5 | Inline editing (edit_message_reply_markup) | Nova mensagem | Nao polui o chat |
| 6 | Apenas `screen_type` no user_data | Estado completo no user_data | Simplicidade — minimo necessario |
| 7 | Telas de nivel e topico SEM compressao | Compressao em tudo | Sao acoes rapidas e decisivas |
| 8 | `user_data` para rastrear tela | `bot_data` / global | Por usuario: cada um ve sua propria tela |

---

## 13. Checklist de Implementacao

- [ ] Criar `collapse_keyboard()` em `keyboards.py`
- [ ] Adicionar `show_more_options` e `hide_options` no `handle_callback()`
- [ ] Criar `_expand_options()` e `_collapse_options()` em `callbacks.py`
- [ ] Criar `_get_keyboard_for_screen()` em `callbacks.py`
- [ ] Modificar `conversation_buttons()` para aceitar parametro opcional
- [ ] Modificar `main_menu()` para aceitar parametro opcional
- [ ] Modificar `vocab_pagination()` para aceitar parametro opcional
- [ ] Modificar `topics_menu()` para aceitar parametro opcional
- [ ] Adicionar `context.user_data["screen_type"]` em todas as telas
- [ ] Atualizar `handle_message()` para usar estado comprimido
- [ ] Atualizar `commands.py` (reset, vocab, topic) para estado comprimido
- [ ] Atualizar `start.py` para estado comprimido
- [ ] Atualizar testes unitarios
- [ ] Adicionar fallback seguro se `screen_type` estiver ausente

---

*Fim do documento de especificacao.*
