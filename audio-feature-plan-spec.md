# Spec: Audio Feature Plan — ElevenLabs + Deepgram

> **Versao:** 1.0
> **Data:** 27 de Junho de 2026
> **Tipo:** Spec de Funcionalidade — Audio (STT/TTS)
> **Projeto:** LinguaBot — English Teacher Telegram Bot
> **Status:** Aguardando implementacao

---

## 1. Resumo

Adicionar suporte a **entrada de audio (STT)** e **saida de audio (TTS)** ao LinguaBot. O usuario podera enviar mensagens de voz pelo Telegram, e o bot respondera com texto + audio. O sistema usa **ElevenLabs como TTS primario** (voz Rachel, 10.000 caracteres/mes gratis) e **Deepgram como STT principal** ($200 creditos gratuitos) **e fallback de TTS** caso o ElevenLabs exceda o limite mensal.

O bot mostra uma **previa do que foi transcrito** ("🎤 You said: ...") antes de responder, para que o usuario possa confirmar que foi entendido corretamente.

---

## 2. Stack de Audio

| Funcao | Primario | Limite Gratis | Fallback |
|--------|----------|---------------|----------|
| **STT** (entrada: voz do usuario) | Deepgram | $200 creditos (nao expiram) | N/A |
| **TTS** (saida: voz do bot) | ElevenLabs | 10.000 chars/mes | Deepgram TTS |

### 2.1 ElevenLabs — TTS Primario

| Item | Valor |
|------|-------|
| SDK | `elevenlabs` (pip) |
| Modelo | `eleven_multilingual_v2` |
| Voz | `JBFqnCBsd6RMkjVDRZzb` (Rachel — voz feminina americana) |
| Free tier | 10.000 caracteres/mes (~1.600 palavras) |
| Rollover | Nao — creditos nao acumulam |
| Formato de saida | `mp3_44100_128` |

### 2.2 Deepgram — STT Principal + TTS Fallback

| Item | STT (Principal) | TTS (Fallback) |
|------|-----------------|----------------|
| SDK | `deepgram-sdk` | `deepgram-sdk` |
| Modelo | `nova-2` (pre-recorded) | `aura-asteria-en` |
| Free tier | $200 creditos unicos | Mesmo pool de $200 |
| Formato audio | Auto-detectado (mp3, wav, ogg, etc.) | |
| Metodo | REST (pre-recorded) — arquivo completo | |

---

## 3. Fluxo do Usuario

### 3.1 Fluxo Normal (ElevenLabs disponivel)

```
Usuario envia audio (voice message)
    |
    v
[1] Bot recebe o audio (Telegram file_id)
    |
    v
[2] Bot faz download do arquivo de audio
    |
    v
[3] Deepgram STT transcreve o audio para texto
    |
    v
[4] Texto transcrito entra no fluxo normal da conversa (Groq)
    |
    v
[5] Groq gera resposta em texto
    |
    v
[6] ElevenLabs TTS converte texto em audio (max 100 chars)
    |
    v
[7] Bot responde com TEXTO + VOICE (nota de voz)
       [🔊 Listen Again] — botao para regerar/ouvir de novo
       [➕ More Options] — botoes comprimidos
```

### 3.2 Fluxo com Fallback (ElevenLabs excedido)

```
[5] Groq gera resposta em texto
    |
    v
[6a] ElevenLabs: limite excedido (10k chars)
    |
    v
[6b] Deepgram TTS: gera audio como fallback
    |
    v
[7] Bot responde com TEXTO + VOICE
       Aviso: "Audio generated via fallback (ElevenLabs limit reached)"
```

### 3.3 Fluxo sem Audio (ambos excedidos)

```
[6a] ElevenLabs: limite excedido
[6b] Deepgram TTS: tambem excedido ou erro
    |
    v
[7] Bot responde apenas com TEXTO
       Aviso: "Audio temporarily unavailable — text reply only"
```

---

## 4. Arquivos a Criar

| Arquivo | Descricao |
|---------|-----------|
| `bot/services/elevenlabs.py` | Cliente ElevenLabs TTS com fallback para Deepgram |
| `bot/services/deepgram.py` | Cliente Deepgram STT (transcricao) + TTS (fallback) |
| `bot/handlers/audio.py` | Handler para mensagens de audio (voice) |
| `bot/audio_cache.py` | Cache em memoria de audios gerados (dict: hash_texto -> bytes) |

### 4.1 Arquivos a Modificar

| Arquivo | Mudanca |
|---------|---------|
| `bot/config.py` | Nenhuma — chaves DEEPGRAM_API_KEY e ELEVENLABS_API_KEY ja existem |
| `bot/main.py` | Registrar `AudioService` e handler de audio no `bot_data` |
| `bot/handlers/message.py` | Modificar `handle_message` para aceitar texto transcrito de audio |
| `bot/utils/keyboards.py` | Adicionar `listen_again_button()` |
| `bot/handlers/callbacks.py` | Adicionar callback `listen_again` |
| `requirements.txt` | Adicionar `elevenlabs` e `deepgram-sdk` |

---

## 5. Detalhamento dos Servicos

### 5.1 `bot/services/elevenlabs.py`

```python
"""
LinguaBot --- ElevenLabs TTS Client

Gera audio a partir de texto usando ElevenLabs API.
Inclui:
  - Fallback automatico para Deepgram TTS quando limite e excedido
  - Cache em memoria de audios gerados (por hash do texto)
  - Truncamento automatico para 100 caracteres
"""

class ElevenLabsService:
    def __init__(self, api_key: str, deepgram_service=None):
        self.api_key = api_key
        self.deepgram = deepgram_service  # fallback TTS
        self._client = None
        self.monthly_chars_used = 0
        self.max_chars = 10000

    async def generate_speech(self, text: str) -> Optional[bytes]:
        """Gera audio a partir do texto. Retorna bytes MP3 ou None.

        Fluxo:
          1. Trunca texto para 100 chars
          2. Verifica cache (hash do texto)
          3. Se ElevenLabs tem cota: usa ElevenLabs
          4. Se ElevenLabs excedeu: usa Deepgram TTS (fallback)
          5. Se ambos falharam: retorna None (resposta so texto)
        """
        ...

    def _truncate_text(self, text: str, max_chars: int = 100) -> str:
        """Trunca o texto para no maximo max_chars caracteres,
        mantendo a frase completa (corta no ultimo ponto antes do limite)."""
        ...
```

### 5.2 `bot/services/deepgram.py`

```python
"""
LinguaBot --- Deepgram Client

Dois modos:
  1. STT (pre-recorded): Transcreve audio do usuario para texto
  2. TTS (fallback): Gera audio quando ElevenLabs esta indisponivel
"""

class DeepgramService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    async def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """Transcreve audio do usuario usando Deepgram STT (nova-2).

        Args:
            audio_bytes: Conteudo do arquivo de audio (mp3/ogg/wav)

        Returns:
            Texto transcrito, ou None se falhou.
        """
        ...

    async def generate_speech(self, text: str) -> Optional[bytes]:
        """Gera audio TTS via Deepgram (modelo aura-asteria-en).

        Usado como FALLBACK quando ElevenLabs excede o limite mensal.

        Args:
            text: Texto a ser convertido em audio (max 100 chars)

        Returns:
            Bytes do audio MP3, ou None se falhou.
        """
        ...
```

### 5.3 `bot/handlers/audio.py`

```python
"""
LinguaBot --- Audio Handler

Recebe mensagens de voz/audio do Telegram:
  1. Faz download do arquivo de audio
  2. Envia para Deepgram STT
  3. Texto transcrito entra no fluxo normal da conversa
  4. Resposta e gerada com texto + audio (ElevenLabs)

So processa audio se o usuario ja tiver conversa ativa.
"""
```

### 5.3a Regra: Audio Apenas para Conversas

O audio (TTS) e gerado **apenas para respostas de conversa** — ou seja,
quando o usuario esta interagindo via mensagens de texto no fluxo normal
(`handle_message`). As seguintes telas **NAO geram audio**:

| Tela / Acao | Motivo |
|-------------|--------|
| `/level` — selecao de nivel | Acao de configuracao, nao de conversa |
| `/help` — ajuda | Texto informativo estatico |
| `/vocab` — vocabulario | Listagem de dados, nao conversa |
| `/topic` — sugestao de topico | Convite, nao resposta de conversa |
| `How it Works` — explicacao | Texto informativo estatico |
| `More Examples` | Acoes de callback (ficam sem audio) |
| `Explain This Word` | Acoes de callback (ficam sem audio) |
| `Practice This` | Acoes de callback (ficam sem audio) |

**So gera audio quando:**
- Usuario envia mensagem de texto (fluxo `handle_message`)
- Usuario envia audio (fluxo `handle_audio` -> Groq -> TTS)
- Botao `Listen Again` (regenera audio da ultima resposta)

### 5.4 `bot/audio_cache.py`

```python
"""
LinguaBot --- Audio Cache

Cache em memoria de audios gerados (TTS).
Usa hash MD5 do texto como chave para evitar
regerar o mesmo audio multiplas vezes.

E um cache volatil — perdido ao restart do bot.
"""

class AudioCache:
    def __init__(self):
        self._cache: dict[str, bytes] = {}

    def get(self, text: str) -> Optional[bytes]:
        ...

    def set(self, text: str, audio: bytes) -> None:
        ...

    def clear(self) -> None:
        ...
```

---

## 6. Detalhamento do Handler de Audio

### 6.1 Registro em `main.py`

```python
# No bot_data
application.bot_data["deepgram"] = DeepgramService(config.deepgram_api_key)
application.bot_data["elevenlabs"] = ElevenLabsService(
    api_key=config.elevenlabs_api_key,
    deepgram_service=application.bot_data["deepgram"],
)

# Handler para mensagens de voz/audio
application.add_handler(
    MessageHandler(filters.VOICE | filters.AUDIO, handle_audio)
)
```

### 6.2 `handle_audio()` — Fluxo

```python
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de voz/audio do usuario."""

    # 1. So processa se ja houver conversa ativa
    conv_mgr = context.bot_data.get("conversation_mgr")
    conv = conv_mgr.get_or_create(user_id)
    if not conv.get_history():
        await update.message.reply_text(
            "Let's start with text first! Say something like 'Hello!' to begin. 😊"
        )
        return

    # 2. Mostra indicador "processando..."
    await update.message.chat.send_action(action="record_audio")

    # 3. Download do audio
    voice = update.message.voice or update.message.audio
    file = await voice.get_file()
    audio_bytes = await file.download_as_bytearray()

    # 4. STT com Deepgram (idioma forcado: ingles)
    deepgram: DeepgramService = context.bot_data.get("deepgram")
    transcribed_text = await deepgram.transcribe_audio(bytes(audio_bytes))

    if not transcribed_text:
        await update.message.reply_text(
            "Sorry, I couldn't understand the audio. "
            "Please try again or type your message! 🎤"
        )
        return

    # 5. SEMPRE mostra previa do que foi entendido
    # (para confirmacao do usuario antes de responder)
    preview = await update.message.reply_text(
        f"🎤 *You said:* {transcribed_text}\n\n"
        "Let me respond...",
        parse_mode="Markdown",
    )

    # 6. Entra no fluxo normal da conversa (Groq) — assincrono
    # Reusa handle_message logica ou chama groq diretamente
    ...

    # 7. Gera audio da resposta com ElevenLabs (assincrono)
    elevenlabs: ElevenLabsService = context.bot_data.get("elevenlabs")
    audio_bytes = await elevenlabs.generate_speech(reply_text)

    if audio_bytes:
        # Remove a mensagem de previa antes de enviar resposta final
        try:
            await preview.delete()
        except Exception:
            pass

        # Envia como nota de voz + texto
        await update.message.reply_voice(
            voice=audio_bytes,
            caption=reply_text,  # texto como legenda do audio
            reply_markup=conversation_buttons(expanded=False, has_audio=True),
        )
    else:
        # Fallback: so texto (previa permanece)
        await update.message.reply_text(
            reply_text,
            reply_markup=conversation_buttons(expanded=False),
        )
```

**Nota:** A mensagem de previa ("🎤 You said: ...") e **sempre mostrada**. Se o audio for gerado com sucesso, a previa e removida e substituida pela resposta com audio + texto. Se o audio falhar, a previa permanece e a resposta vem como texto normal.

### 6.3 Botao "Listen Again"

Um novo botao aparece na linha de botoes expandidos:

```python
def listen_again_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("🔊 Listen Again", callback_data="listen_again")
```

Adicionar na `conversation_buttons()` expandida:

```python
# Quando expanded=True, o teclado da conversa inclui:
[
    [📝 More Examples,  📖 Explain This Word],
    [🎯 Practice This],
    [🔊 Listen Again],                          # NOVO
    [◀ Hide Options],
]
```

O callback `listen_again`:
1. Pega o texto da ultima resposta do assistente na conversa
2. Gera audio via ElevenLabs (com cache)
3. Envia como **nova mensagem de voz separada** (reply a mensagem anterior)
4. Nao edita/remove a mensagem anterior — apenas envia uma nova

---

## 7. Gerenciamento de Limite ElevenLabs (10.000 chars/mes)

### 7.1 Rastreamento

```python
# Atributo da classe ElevenLabsService
self.monthly_chars_used = 0
self.max_chars = 10000

# A cada TTS, incrementa:
self.monthly_chars_used += len(truncated_text)
```

**Nota:** O contador e **em memoria** — reinicia se o bot for restartado. Para um controle mais preciso, seria necessario consultar a API do ElevenLabs ou persistir o contador. A abordagem em memoria e aceitavel para MVP (1 usuario).

### 7.2 Limiares de Aviso

| Uso | Ação |
|-----|------|
| **0-70%** (0-7k chars) | Normal — gera audio sem aviso |
| **70-90%** (7k-9k chars) | Aviso no log + mensagem ao usuario: *"You've used {X}% of this month's audio limit"* |
| **90-100%** (9k-10k chars) | Aviso mais forte: *"Almost out of audio! Only {Y} characters remaining this month"* |
| **>100%** (>10k chars) | Ativa fallback para Deepgram TTS automaticamente |

### 7.3 Mensagens de Status (Embutidas na Resposta)

O aviso e **embutido no final da resposta normal** do bot, como uma linha extra no mesmo texto:

```python
# No texto da resposta, apos o conteudo principal:
if pct >= 70:
    reply_text += f"\n\n💡 *Audio usage:* {self.monthly_chars_used}/{self.max_chars} chars this month"

# Exemplo final:
# "Great job! Keep practicing! 🎉"
# "💡 Audio usage: 7,500/10,000 chars this month"
```

Nao cria mensagem separada — apenas uma linha extra ao final do texto ja enviado.

---

## 8. Tabela de Vozes

| Provedor | Modelo/Voz | Uso | Idioma |
|----------|-----------|-----|--------|
| **ElevenLabs** | `eleven_multilingual_v2` + Rachel | TTS primario | Ingles (multilingue) |
| **Deepgram TTS** | `aura-asteria-en` | TTS fallback | Ingles |
| **Deepgram STT** | `nova-2` | STT (transcricao) | Ingles (forcado: `language: "en"`) |

---

## 9. Tratamento de Erros

### 9.1 Cenarios Especificos

| Cenario | Comportamento |
|---------|---------------|
| Audio do usuario corrompido / muito curto | Mensagem: *"I couldn't hear anything. Please speak clearly and try again! 🎤"* |
| Deepgram STT retorna vazio | Mensagem: *"I couldn't understand the audio. Try typing instead!"* |
| ElevenLabs API timeout | Tentar novamente 1x. Se falhar, usar Deepgram TTS fallback |
| ElevenLabs + Deepgram TTS ambos falham | Resposta apenas em texto, sem audio |
| Usuario envia audio sem conversa ativa | Mensagem: *"Let's start with text first! Say 'Hello!' to begin. 😊"* |
| Arquivo de audio muito grande (>20MB) | Mensagem: *"Your audio is too long. Please send a shorter message! 🎤"* |

### 9.2 Retry

Mesmo padrao do GroqService:
- 2 tentativas com backoff de 2 segundos
- Se todas falharem: fallback para proximo provedor
- Se todos os provedores falharem: resposta apenas em texto

---

## 10. Modificacoes no Keyboard

### 10.1 `conversation_buttons` — Versao Expandida com Audio

```python
def conversation_buttons(expanded: bool = False, has_audio: bool = False) -> InlineKeyboardMarkup:
    if expanded:
        keyboard = [
            [MORE_EXAMPLES_BTN, EXPLAIN_WORD_BTN],
            [PRACTICE_THIS_BTN],
        ]
        if has_audio:
            keyboard.append([LISTEN_AGAIN_BTN])  # 🔊 Listen Again
        keyboard.append([HIDE_BUTTON])
        return InlineKeyboardMarkup(keyboard)

    return InlineKeyboardMarkup([[MORE_BUTTON]])
```

### 10.2 Novo Botao

```python
LISTEN_AGAIN_BTN = InlineKeyboardButton("\U0001f50a Listen Again", callback_data="listen_again")
```

### 10.3 Novo Callback

```python
elif data == "listen_again":
    await _listen_again(query, context)
```

---

## 11. Dependencias

Adicionar ao `requirements.txt`:

```
elevenlabs>=1.0.0
deepgram-sdk>=3.0.0
```

---

## 12. Estrutura de Arquivos (Apos Implementacao)

```
bot/
├── services/
│   ├── elevenlabs.py      # NOVO — TTS cliente
│   ├── deepgram.py        # NOVO — STT + TTS fallback
├── handlers/
│   ├── audio.py           # NOVO — handler de mensagens de voz
├── audio_cache.py         # NOVO — cache de audios em memoria
├── utils/
│   ├── keyboards.py       # MODIFICADO — novo botao Listen Again
├── handlers/
│   ├── callbacks.py       # MODIFICADO — novo callback listen_again
├── main.py                # MODIFICADO — registra servicos e handler
├── config.py              # INALTERADO — chaves ja existem
└── requirements.txt       # MODIFICADO — novas dependencias
```

---

## 13. Fases de Implementacao

### Fase 1 — Base (prioridade maxima)

1. Instalar dependencias (`elevenlabs`, `deepgram-sdk`)
2. Criar `bot/audio_cache.py` (cache em memoria)
3. Criar `bot/services/deepgram.py` (STT + TTS fallback)
4. Criar `bot/services/elevenlabs.py` (TTS primario com fallback)
5. Registrar servicos no `bot_data` em `main.py`

### Fase 2 — Handler de Audio

6. Criar `bot/handlers/audio.py`
7. Adicionar `MessageHandler(filters.VOICE | filters.AUDIO, handle_audio)`
8. Implementar fluxo: download -> STT -> Groq -> TTS -> resposta

### Fase 3 — Botao Listen Again

9. Adicionar `LISTEN_AGAIN_BTN` em `keyboards.py`
10. Adicionar callback `listen_again` em `callbacks.py`
11. Integrar botao no teclado expandido de conversa

### Fase 4 — Testes

12. Testes para `DeepgramService.transcribe_audio()` (mockado)
13. Testes para `ElevenLabsService.generate_speech()` (mockado)
14. Testes para `AudioCache` (get/set/clear)
15. Testes para `handle_audio` (fluxo completo mockado)
16. Testar truncamento de texto (max 100 chars, manter frase completa)

---

## 14. Checklist de Implementacao

- [ ] Instalar `elevenlabs` e `deepgram-sdk`
- [ ] Criar `bot/audio_cache.py`
- [ ] Criar `bot/services/deepgram.py` (STT + TTS)
- [ ] Criar `bot/services/elevenlabs.py` (TTS primario)
- [ ] Registrar servicos em `main.py`
- [ ] Criar `bot/handlers/audio.py` (handle_audio)
- [ ] Adicionar MessageHandler para VOICE/AUDIO
- [ ] Adicionar `LISTEN_AGAIN_BTN` em `keyboards.py`
- [ ] Adicionar callback `listen_again` em `callbacks.py`
- [ ] Implementar truncamento de texto (300 chars)
- [ ] Implementar cache em memoria (hash -> bytes)
- [ ] Implementar fallback ElevenLabs -> Deepgram TTS
- [ ] Implementar avisos de limite (70%, 90%, 100%)
- [ ] Validar que so processa audio se conversa ativa
- [ ] Testes unitarios (mockados)
- [ ] Atualizar /help e How it Works com novo recurso

---

## 15. Registro de Decisoes

| # | Decisao | Alternativa | Motivo |
|---|---------|-------------|--------|
| 1 | ElevenLabs TTS (primario) + Deepgram TTS (fallback) | So ElevenLabs | Aproveitar $200 creditos do Deepgram |
| 2 | Deepgram STT como unico STT | Whisper / Google STT | $200 gratis, SDK Python maduro |
| 2b | Deepgram STT forcado para ingles | Auto-detect | Evitar transcricao acidental de portugues |
| 3 | Voz Rachel (feminina americana) | Voz masculina / brasileira | Clareza para alunos de ingles |
| 4 | Sempre audio + texto | So audio / so texto | Acessibilidade: ler e ouvir |
| 5 | Truncar em 100 chars | Audio completo / 150 chars | Economizar caracteres ElevenLabs |
| 6 | Nota de voz (send_voice) | Arquivo de audio | Experiencia nativa no Telegram |
| 7 | Cache em memoria | Cache em disco | Simplicidade, dados nao persistem |
| 8 | So processa audio se conversa ativa | Sempre processa | Evitar transcricao sem contexto |
| 9 | Contador de uso em memoria | Consultar API ElevenLabs | Simplicidade para MVP |
| 10 | Botao Listen Away no estado expandido | Botao sempre visivel | Consistencia com sistema de compressao |
| 11 | **Audio APENAS para conversas** | Audio para todas as respostas | Economizar caracteres ElevenLabs; acoes de menu nao precisam de audio |

---

## 16. Glossario

| Termo | Significado |
|-------|-------------|
| **TTS** | Text-to-Speech — conversao de texto em audio |
| **STT** | Speech-to-Text — transcricao de audio em texto |
| **Pre-recorded** | Audio completo processado de uma vez (vs. streaming em tempo real) |
| **Voice message** | Mensagem de voz nativa do Telegram (formato OGG/Opus) |
| **Fallback** | Provedor alternativo usado quando o primario falha |
| **Cache hit** | Audio ja existente no cache, nao precisa regerar |

---

*Fim do documento de especificacao.*
