# Spec: Audio Personalization & Expressive Responses

> **Versão:** 1.0
> **Data:** 28 de Junho de 2026
> **Status:** Draft

---

## 1. Resumo

Três melhorias para tornar as respostas do LinguaBot mais naturais, personalizadas e alinhadas às preferências do usuário:

1. **Velocidade do áudio personalizável** — usuário escolhe entre 5 opções (0.75x a 1.25x), integrado ao comando `/voice`
2. **Respostas emocionalmente expressivas** — Groq varia o tom emocional (entusiasmo, calma, curiosidade, seriedade) em texto natural, influenciando a entonação do TTS
3. **Qualidade das respostas por nível refinada** — system prompts atualizados para incluir variação emocional perceptível entre respostas

---

## 2. Velocidade do Áudio

### 2.1 Comportamento

O usuário pode personalizar a velocidade da fala nos áudios gerados pelo TTS.

- **Range:** 0.75x a 1.25x
- **Passo:** 0.05 (onze valores possíveis)
- **UI simplificada:** 5 botões no `/voice`
- **Padrão por nível:**
  - A1: 0.85x (mais lento, ideal para iniciantes acompanharem)
  - A2: 0.9x (ligeiramente mais lento)
  - B1: 1.0x (velocidade natural)
- **Persistência:** salvo em `user_data["tts_speed"]`
- **Escopo:** aplica tanto ao Deepgram Aura (primário) quanto ao ElevenLabs (fallback)
- **Reset ao mudar de nível:** sim — se o usuário trocar de nível (ex: A1 → B1), a velocidade volta ao padrão do novo nível (1.0x)

### 2.2 Interface no /voice

O comando `/voice` atualmente mostra as 4 opções de voz + botão "Current Voice". Será expandido para incluir:

```
🔊 Current Voice: Thalia
Feminine, clear, confident, energetic

Choose a different voice:
[🔊 Thalia]  [Odysseus]  [Helena]  [Mars]

Speaking Speed:
[🐢 0.75x] [0.85x] [1.0x ●] [1.15x] [🐇 1.25x]

[◀️ Back to Menu]
```

- O valor atual (padrão ou personalizado) terá um marcador (●)
- Emojis de tartaruga (🐢) e coelho (🐇) nas pontas para indicar lento/rápido
- Botão de voltar ao menu existente permanece

### 2.3 Fluxo de seleção

```
Usuário: /voice
Bot: Mostra tela com vozes + velocidade
Usuário clica: 0.85x
Bot: ✅ Speed set to 0.85x! (resposta editada na mesma mensagem)
        I'll speak a bit slower for you.

Usuário clica: Thalia
Bot: ✅ Voice updated to Thalia!
        Feminine, clear, confident, energetic
```

### 2.4 Callbacks

| Callback | Ação |
|----------|------|
| `set_speed_0.75` | Define `user_data["tts_speed"] = 0.75` |
| `set_speed_0.85` | Define `user_data["tts_speed"] = 0.85` |
| `set_speed_1.0` | Define `user_data["tts_speed"] = 1.0` |
| `set_speed_1.15` | Define `user_data["tts_speed"] = 1.15` |
| `set_speed_1.25` | Define `user_data["tts_speed"] = 1.25` |

### 2.5 Persistência

```python
# Em user_data
context.user_data["tts_speed"] = 0.85  # float

# Padrão por nível (definido quando o nível muda ou speed não foi personalizado)
DEFAULT_SPEED_BY_LEVEL = {
    "A1": 0.85,
    "A2": 0.9,
    "B1": 1.0,
}
```

### 2.6 Implementação no TTS

#### Deepgram Aura (deepgram_tts.py)

Adicionar parâmetro `speed` ao método `generate_speech()`:

```python
async def generate_speech(self, text: str, voice_id: str = DEFAULT_VOICE_ID, speed: float = 1.0) -> Optional[bytes]:
```

Passar para a API:

```python
chunks = client.speak.v1.audio.generate(
    text=text,
    model=voice_id,
    encoding="mp3",
    speed=speed,  # NOVO
)
```

Nota: as docs do Deepgram são contraditórias sobre o suporte a `speed` no modelo Aura-2. Se a API ignorar o parâmetro ou retornar erro, o DeepgramTTSService deve simplesmente cair para speed=1.0 (sem quebrar).

#### ElevenLabs (elevenlabs.py)

Adicionar suporte a `speed` via modelo ElevenLabs:

```python
chunks = client.text_to_speech.convert(
    voice_id=DEFAULT_VOICE_ID,
    text=text,
    model_id=MODEL_ID,
    output_format=OUTPUT_FORMAT,
    # ElevenLabs usa 'speed' como parâmetro opcional em alguns modelos
)
```

Se a API não suportar, ignorar silenciosamente.

### 2.7 Reset de speed ao mudar de nível

No callback `_set_level` em `callbacks.py`, adicionar:

```python
# Reseta velocidade ao padrão do novo nível
new_speed = DEFAULT_SPEED_BY_LEVEL.get(level, 1.0)
context.user_data["tts_speed"] = new_speed
```

---

## 3. Respostas Emocionalmente Expressivas

### 3.1 Conceito

O Groq (modelo de IA) é instruído via system prompt a variar o tom emocional das respostas usando **linguagem natural expressiva** — sem SSML, sem tags especiais. O Deepgram Aura lê o texto naturalmente, e a entonação natural do TTS acompanha o conteúdo emocional do texto.

### 3.2 Como funciona

```
[System Prompt] → Groq gera texto expressivo → Deepgram lê o texto
                                                      ↓
                                              Entonação natural
                                              acompanha o texto
```

### 3.3 O que muda no system prompt

Adicionar ao **SYSTEM_PROMPT_BASE** em `groq.py`:

```
EMOTIONAL TONE:
- Vary your emotional tone naturally based on the context.
- Be EXPressive — this is a conversation, not a robot reading text.
- Use natural emotional language: exclamations, enthusiasm, curiosity, warmth.
- Examples of tonal variation:
  ✅ Student gets it right: "Excellent! You nailed it! 🎉 That's perfect!"
  ✅ Explaining a concept: "Let me show you... it's actually quite simple."
  ✅ Asking a question: "I'm curious — what do you think about that?"
  ✅ Gentle correction: "Almost there! Just a small fix..."
  ✅ Encouraging: "You're getting so much better! Keep going! 💪"
  ✅ Serious topic: "That's a good question. Let me explain carefully..."
- Avoid being monotone or robotic. Vary sentence length and punctuation.
- Use rhetorical questions, exclamations, and thoughtful pauses.
- Match the energy of the student — if they're excited, be excited too!
```

### 3.4 Decisões de design

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Quem decide a emoção | Groq (IA) automaticamente | Natural e contextual |
| Varia por nível? | Não — igual para todos | Consistência, IA adapta ao contexto |
| Como expressar | Texto natural (exclamações, pausas) | Deepgram não suporta SSML |
| Tom padrão | Sempre encorajador e positivo | Essência do bot |

### 3.5 Impacto no GroqService

Nenhuma mudança de código no `GroqService` — apenas o system prompt é atualizado. O `generate_reply()` já usa `get_system_prompt(level)` que monta o prompt completo.

A alteração é no `SYSTEM_PROMPT_BASE` (compartilhado por todos os níveis) — a seção `CORE RULES` ganha novas regras de tom emocional.

---

## 4. Alterações nos Arquivos

### 4.1 Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `bot/services/groq.py` | Adicionar seção "EMOTIONAL TONE" ao SYSTEM_PROMPT_BASE |
| `bot/services/deepgram_tts.py` | Adicionar parâmetro `speed` ao `generate_speech()` e `_try_deepgram()` |
| `bot/services/elevenlabs.py` | Adicionar parâmetro `speed` ao `generate_speech()` e `_try_elevenlabs()` |
| `bot/handlers/voice_command.py` | Adicionar seção de velocidade à tela; mostrar speed atual |
| `bot/handlers/callbacks.py` | Adicionar callbacks `set_speed_X.XX`; resetar speed ao mudar de nível |
| `bot/handlers/audio.py` | Passar `speed` de `user_data` para `deepgram_tts.generate_speech()` e `elevenlabs.generate_speech()` |
| `bot/handlers/message.py` | Passar `speed` de `user_data` para `deepgram_tts.generate_speech()` e `elevenlabs.generate_speech()` |
| `bot/utils/keyboards.py` | Adicionar `voice_speed_keyboard()` ou expandir `voice_selection_keyboard()` |

### 4.2 Constantes Compartilhadas

Criar em `bot/config.py` ou um novo arquivo `bot/services/tts_config.py`:

```python
# Opções de velocidade disponíveis no /voice
SPEED_OPTIONS = [0.75, 0.85, 1.0, 1.15, 1.25]

# Velocidade padrão por nível
DEFAULT_SPEED_BY_LEVEL = {
    "A1": 0.85,
    "A2": 0.9,
    "B1": 1.0,
}
```

Ou manter em `bot/utils/keyboards.py` se forem usadas apenas lá.

---

## 5. Teclado de Velocidade

### 5.1 voice_selection_keyboard() expandido

Em `bot/utils/keyboards.py`, expandir a função existente para incluir opções de velocidade:

```python
def voice_selection_keyboard(current_voice_id: str, current_speed: float = 1.0) -> InlineKeyboardMarkup:
    """Botoes para escolha de voz + velocidade. SEM compressao — sempre visivel."""
    from bot.services.deepgram_tts import VOICES

    keyboard = []
    # Seção de vozes
    for vid, name, desc in VOICES:
        label = f"🔊 {name}" if vid == current_voice_id else f"{name}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"set_voice_{vid}")])

    # Seção de velocidade
    speed_row = []
    for speed_val in SPEED_OPTIONS:
        emoji = "🐢" if speed_val == 0.75 else "🐇" if speed_val == 1.25 else ""
        label = f"{emoji} {speed_val}x" if speed_val == current_speed else f"{speed_val}x"
        speed_row.append(InlineKeyboardButton(label, callback_data=f"set_speed_{speed_val}"))
    keyboard.append(speed_row)

    keyboard.append([InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)
```

### 5.2 Callbacks de velocidade

Em `bot/handlers/callbacks.py`, adicionar:

```python
# No roteador handle_callback:
elif data.startswith("set_speed_"):
    speed_str = data[len("set_speed_"):]
    speed = float(speed_str)
    await _set_speed(query, context, speed)
```

```python
async def _set_speed(query, context: ContextTypes.DEFAULT_TYPE, speed: float) -> None:
    """Define a velocidade do TTS para o usuario."""
    user_id = query.from_user.id

    # Salva preferencia
    context.user_data["tts_speed"] = speed

    # Mostra indicador visual
    speed_indicators = {
        0.75: "🐢 Very slow",
        0.85: "Slow",
        1.0: "Normal",
        1.15: "Fast",
        1.25: "🐇 Very fast",
    }

    text = (
        f"✅ **Speed set to {speed}x!**\n\n"
        f"{speed_indicators.get(speed, '')}\n\n"
        "I'll use this speed for my audio responses. "
        "You can change it anytime with /voice"
    )

    await query.edit_message_text(
        text,
        reply_markup=back_to_menu_button(),
        parse_mode="Markdown",
    )
```

---

## 6. Passagem de Speed nos Handlers

### 6.1 audio.py

```python
# Obter velocidade
speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))

# Passar para Deepgram
audio_bytes = await deepgram_tts.generate_speech(display_text, voice_id=voice_id, speed=speed)

# Passar para ElevenLabs fallback
audio_bytes = await elevenlabs.generate_speech(display_text, speed=speed)
```

### 6.2 message.py

Mesmo padrão do `audio.py`.

---

## 7. Fluxo de Reset ao Mudar de Nível

### 7.1 callbacks.py — _set_level

```python
async def _set_level(query, context: ContextTypes.DEFAULT_TYPE, level: str) -> None:
    # ... código existente ...

    # Reseta velocidade ao padrão do novo nível
    new_speed = DEFAULT_SPEED_BY_LEVEL.get(level, 1.0)
    context.user_data["tts_speed"] = new_speed

    # ... continua ...
```

---

## 8. Deepgram `speed` Parameter

### 8.1 Contradição nas docs

As documentações do Deepgram são contraditórias quanto ao suporte do parâmetro `speed` no modelo Aura-2:

- Uma fonte indica que `speed` (double, multiplicador) existe e preserva prosódia natural
- Outra indica que o Aura TTS não aceita parâmetro de velocidade

**Decisão:** Implementar o parâmetro e testar. Se a API ignorar ou falhar, o código trata graciosamente (fallback para speed=1.0). O ElevenLabs também receberá o parâmetro.

### 8.2 Tratamento de erro

```python
async def _try_deepgram(self, text: str, voice_id: str = DEFAULT_VOICE_ID, speed: float = 1.0) -> Optional[bytes]:
    try:
        client = self._get_client()
        chunks = client.speak.v1.audio.generate(
            text=text,
            model=voice_id,
            encoding="mp3",
            **({"speed": speed} if speed != 1.0 else {}),
        )
        # ...
    except Exception as e:
        logger.warning("Deepgram Aura falhou (voice: %s, speed: %s): %s", voice_id, speed, e)
        # Se falhou com speed != 1.0, tentar sem speed
        if speed != 1.0:
            logger.info("Tentando sem speed parameter...")
            return await self._try_deepgram(text, voice_id=voice_id, speed=1.0)
        return None
```

---

## 9. Testes

### 9.1 Testes Novos

| Teste | Descrição |
|-------|-----------|
| `test_set_speed_callback` | Callback `set_speed_0.85` salva 0.85 em user_data |
| `test_default_speed_by_level` | A1 → 0.85, A2 → 0.9, B1 → 1.0 |
| `test_speed_reset_on_level_change` | Mudar de A1 para B1 reseta speed para 1.0 |
| `test_speed_passed_to_deepgram` | `generate_speech` recebe speed do user_data |
| `test_voice_command_shows_speed` | /voice exibe velocidade atual |
| `test_emotional_tone_in_system_prompt` | SYSTEM_PROMPT_BASE contém seção EMOTIONAL TONE |

### 9.2 Testes Modificados

| Teste | Mudança |
|-------|---------|
| `test_voice_selection_keyboard` | Verificar que teclado agora inclui botões de speed |

---

## 10. Decisões de Design Consolidadas

| # | Decisão | Alternativa | Motivo |
|---|---------|-------------|--------|
| 1 | Speed varia por nível (A1=0.85, B1=1.0) | Speed fixo para todos | Iniciantes precisam de fala mais lenta |
| 2 | Speed integrado ao /voice | Comando separado /speed | Menos comandos, UI unificada de áudio |
| 3 | 5 opções simplificadas de speed | 11 opções ou slider | UI limpa para Telegram |
| 4 | Speed reseta ao mudar de nível | Mantém personalização | Padrão do nível é pedagogicamente correto |
| 5 | Emoção via texto natural | SSML ou tags especiais | Deepgram não suporta SSML |
| 6 | Emoção igual para todos os níveis | Emoção varia por nível | Groq adapta naturalmente ao contexto |
| 7 | Groq decide emoção automaticamente | Usuário escolhe tom | Mais natural e contextual |
| 8 | Speed aplica a Deepgram + ElevenLabs | Só Deepgram | Consistência na experiência do usuário |
| 9 | Speed testado com fallback se falhar | Ignorar se falhar | Resiliência sem quebrar o fluxo |
| 10 | Descritor emocional no system prompt | Prompt separado | Reutiliza estrutura existente de prompts |

---

## 11. Checklist de Implementação

- [ ] Atualizar `SYSTEM_PROMPT_BASE` em `groq.py` com seção EMOTIONAL TONE
- [ ] Definir `SPEED_OPTIONS` e `DEFAULT_SPEED_BY_LEVEL` (em `config.py` ou `keyboards.py`)
- [ ] Adicionar `speed` a `DeepgramTTSService.generate_speech()` e `_try_deepgram()`
- [ ] Adicionar `speed` a `ElevenLabsService.generate_speech()` e `_try_elevenlabs()`
- [ ] Expandir `voice_selection_keyboard()` para incluir botões de speed em `keyboards.py`
- [ ] Adicionar callbacks `set_speed_X.XX` no roteador `handle_callback` em `callbacks.py`
- [ ] Criar `_set_speed()` em `callbacks.py`
- [ ] Modificar `_set_level()` para resetar speed ao padrão do novo nível
- [ ] Passar `speed` de `user_data` em `audio.py` e `message.py`
- [ ] Atualizar `voice_command.py` para mostrar speed atual
- [ ] Testes unitários
- [ ] Rodar suite completa de testes
