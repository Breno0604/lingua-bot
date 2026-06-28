# TTSOrchestrator — Serviço Unificado de Geração de Áudio

## 1. Problema

O código de geração de áudio está **duplicado** em dois handlers:

| Arquivo | Linhas duplicadas | Diferenças no pós-áudio |
|---------|-------------------|------------------------|
| `bot/handlers/audio.py` | ~15 linhas (seção 8) | Envia voz com botões; fallback usa `edit_reply_markup` no texto |
| `bot/handlers/message.py` | ~15 linhas (seção "Gera audio") | Envia texto + voz com botões; fallback envia texto com botões direto |

**Impacto:** ~30 linhas de lógica idêntica mantidas em dois lugares — qualquer alteração no fluxo TTS (ex: adicionar um cache compartilhado, novo provedor, ou mudar fallback) precisa ser replicada em ambos.

---

## 2. Código Duplicado (antes da extração)

O bloco a seguir aparece em `audio.py` e `message.py` com diferenças mínimas:

```python
# ── Gera audio da resposta ──
deepgram_tts = context.bot_data.get("deepgram_tts")
elevenlabs = context.bot_data.get("elevenlabs")
audio_bytes = None

if deepgram_tts:
    voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
    speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))
    audio_bytes = await deepgram_tts.generate_speech(display_text, voice_id=voice_id, speed=speed)

# Fallback: ElevenLabs
if not audio_bytes and elevenlabs:
    logger.info("Deepgram Aura falhou, usando ElevenLabs fallback (text msg)")
    speed = context.user_data.get("tts_speed", 1.0)
    audio_bytes = await elevenlabs.generate_speech(display_text, speed=speed)
```

---

## 3. Solução Proposta

### 3.1 Classe `TTSOrchestrator`

Novo arquivo: `bot/services/tts_orchestrator.py`

```python
class TTSOrchestrator:
    def __init__(self, deepgram_tts: DeepgramTTSService | None, elevenlabs: ElevenLabsService | None):
        self.deepgram_tts = deepgram_tts
        self.elevenlabs = elevenlabs

    async def generate_audio(
        self,
        text: str,
        voice_id: str = DG_DEFAULT_VOICE_ID,
        speed: float = 1.0,
    ) -> bytes | None:
        """Gera audio com fallback: Deepgram -> ElevenLabs -> None."""
```

### 3.2 Interface

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `text` | `str` | — | Texto a ser convertido em áudio |
| `voice_id` | `str` | `DG_DEFAULT_VOICE_ID` | Voz Deepgram Aura (ignorada no ElevenLabs) |
| `speed` | `float` | `1.0` | Multiplicador de velocidade (0.75–1.25) |

| Retorno | Significado |
|---------|-------------|
| `bytes` | Áudio MP3 gerado com sucesso |
| `None` | Ambos TTS falharam |

### 3.3 Fluxo Interno

```
generate_audio(text, voice_id, speed)
  │
  ├─ Se deepgram_tts existe:
  │     ├─ audio = deepgram_tts.generate_speech(text, voice_id, speed)
  │     └─ Se audio: return audio
  │
  ├─ Se elevenlabs existe e audio ainda é None:
  │     ├─ audio = elevenlabs.generate_speech(text, speed)
  │     └─ Se audio: return audio
  │
  └─ return None
```

### 3.4 Como os Handlers Chamam

**Antes (duplicado):**
```python
# audio.py e message.py — 15 linhas cada
deepgram_tts = context.bot_data.get("deepgram_tts")
elevenlabs = context.bot_data.get("elevenlabs")
audio_bytes = None
if deepgram_tts:
    voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
    speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))
    audio_bytes = await deepgram_tts.generate_speech(display_text, voice_id=voice_id, speed=speed)
if not audio_bytes and elevenlabs:
    speed = context.user_data.get("tts_speed", 1.0)
    audio_bytes = await elevenlabs.generate_speech(display_text, speed=speed)
```

**Depois (unificado):**
```python
# Cada handler: 4 linhas
tts: TTSOrchestrator = context.bot_data.get("tts_orchestrator")
voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))
audio_bytes = await tts.generate_audio(display_text, voice_id=voice_id, speed=speed)
```

---

## 4. Arquivos a Modificar

| Arquivo | Tipo de mudança | Descrição |
|---------|----------------|-----------|
| `bot/services/tts_orchestrator.py` | **CRIAR** | Nova classe TTSOrchestrator |
| `bot/services/__init__.py` | Editar | Adicionar import (ou deixar vazio como os outros) |
| `bot/main.py` | Editar | Instanciar TTSOrchestrator e registrar em `bot_data["tts_orchestrator"]` |
| `bot/handlers/audio.py` | Editar | Substituir bloco duplicado por chamada ao TTSOrchestrator |
| `bot/handlers/message.py` | Editar | Substituir bloco duplicado por chamada ao TTSOrchestrator |
| `bot/handlers/callbacks.py` | **Não modificar** | Não gera áudio — apenas expande/recolhe botões |
| `tests/conftest.py` | Editar | Adicionar fixture `mock_tts_orchestrator` |
| `tests/test_audio.py` | Editar | Atualizar mocks para usar TTSOrchestrator |
| `tests/test_message.py` | **Criar?** | Atualmente não existe — pode ser feito em PR separado |

---

## 5. Plano de Implementação

### 5.1 Criar `bot/services/tts_orchestrator.py`

```python
"""
LinguaBot --- TTS Orchestrator

Servico unificado de geracao de audio que coordena:
  1. Deepgram Aura (TTS primario, 4 vozes)
  2. ElevenLabs (fallback, voz Rachel)

Centraliza a logica de fallback e resolucao de velocidade.
"""

import logging

from bot.services.deepgram_tts import DeepgramTTSService, DEFAULT_VOICE_ID
from bot.services.elevenlabs import ElevenLabsService

logger = logging.getLogger(__name__)


class TTSOrchestrator:
    """Coordena a geracao de audio entre Deepgram Aura (primario) e ElevenLabs (fallback)."""

    def __init__(
        self,
        deepgram_tts: DeepgramTTSService | None = None,
        elevenlabs: ElevenLabsService | None = None,
    ):
        self.deepgram_tts = deepgram_tts
        self.elevenlabs = elevenlabs

    async def generate_audio(
        self,
        text: str,
        voice_id: str = DEFAULT_VOICE_ID,
        speed: float = 1.0,
    ) -> bytes | None:
        """Gera audio com fallback em cascata: Deepgram -> ElevenLabs -> None.

        Args:
            text: Texto a ser convertido em audio.
            voice_id: Voz Deepgram Aura (ignorada no ElevenLabs).
            speed: Multiplicador de velocidade (0.75 a 1.25).

        Returns:
            Bytes MP3 do audio, ou None se ambos provedores falharem.
        """
        # 1. Tenta Deepgram Aura (primario)
        if self.deepgram_tts:
            audio = await self.deepgram_tts.generate_speech(
                text, voice_id=voice_id, speed=speed,
            )
            if audio is not None:
                return audio

        # 2. Fallback: ElevenLabs
        if self.elevenlabs:
            logger.info("Deepgram Aura falhou, usando ElevenLabs fallback")
            audio = await self.elevenlabs.generate_speech(text, speed=speed)
            if audio is not None:
                return audio

        # 3. Ambos falharam
        logger.warning("Ambos TTS falharam — resposta sem audio")
        return None
```

### 5.2 Atualizar `bot/main.py`

Adicionar na seção de serviços de áudio:

```python
from bot.services.tts_orchestrator import TTSOrchestrator

# Dentro de build_application(), apos criar DeepgramTTSService e ElevenLabsService:

tts_orchestrator = TTSOrchestrator(
    deepgram_tts=deepgram_tts_service,
    elevenlabs=elevenlabs_service if config.elevenlabs_api_key else None,
)
application.bot_data["tts_orchestrator"] = tts_orchestrator
```

### 5.3 Atualizar `bot/handlers/audio.py`

Substituir o bloco de geração de áudio (seção "8. Gera audio da resposta") por:

```python
    # 8. Gera audio via TTSOrchestrator
    tts: TTSOrchestrator = context.bot_data.get("tts_orchestrator")
    audio_bytes = None
    if tts:
        voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
        speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))
        audio_bytes = await tts.generate_audio(display_text, voice_id=voice_id, speed=speed)
```

Remover imports de `DEFAULT_SPEED_BY_LEVEL` (se não for mais usado) e dos serviços TTS individuais (deepgram_tts, elevenlabs) do `audio.py`.

### 5.4 Atualizar `bot/handlers/message.py`

Mesma substituição:

```python
    tts: TTSOrchestrator = context.bot_data.get("tts_orchestrator")
    audio_bytes = None
    if tts:
        voice_id = context.user_data.get("voice_id", DG_DEFAULT_VOICE_ID)
        speed = context.user_data.get("tts_speed", DEFAULT_SPEED_BY_LEVEL.get(user_level, 1.0))
        audio_bytes = await tts.generate_audio(display_text, voice_id=voice_id, speed=speed)
```

### 5.5 Atualizar `tests/conftest.py`

Adicionar fixture:

```python
@pytest.fixture
def mock_tts_orchestrator():
    """Mock do TTSOrchestrator — retorna audio com sucesso."""
    tts = MagicMock()
    tts.generate_audio = AsyncMock(return_value=b"fake_tts_audio")
    return tts
```

### 5.6 Atualizar `tests/test_audio.py`

- Adicionar `mock_tts_orchestrator` ao `configured_audio_context` fixture
- Atualizar `active_conversation` se necessário
- Testes de speed: em vez de verificar `deepgram_tts.generate_speech.call_args`, verificar `tts_orchestrator.generate_audio.call_args.kwargs`:

```python
@pytest.mark.asyncio
async def test_speed_passed_to_tts_orchestrator(self, active_conversation):
    update, context = active_conversation
    context.user_data["tts_speed"] = 0.85
    await handle_audio(update, context)
    tts = context.bot_data["tts_orchestrator"]
    tts.generate_audio.assert_called_once()
    assert tts.generate_audio.call_args.kwargs.get("speed") == 0.85
```

---

## 6. Benefícios

| Métrica | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| Linhas duplicadas | ~30 | 0 | **-100%** |
| Linhas em audio.py (seção TTS) | ~15 | ~5 | **-67%** |
| Linhas em message.py (seção TTS) | ~15 | ~5 | **-67%** |
| Arquivos que precisam mudar p/ novo TTS | 2 (audio + message) | 1 (TTSOrchestrator) | **-50%** |
| Complexidade ciclomática (audio.py) | ~35 | ~30 | **-14%** |
| Complexidade ciclomática (message.py) | ~40 | ~35 | **-12.5%** |

## 7. Testes

### 7.1 Testes do TTSOrchestrator

Novo arquivo: `tests/test_tts_orchestrator.py`

| Teste | Descrição |
|-------|-----------|
| `test_deepgram_primario` | Deepgram retorna audio -> retorna o audio |
| `test_fallback_elevenlabs` | Deepgram falha, ElevenLabs funciona -> retorna audio do ElevenLabs |
| `test_ambos_falham` | Ambos retornam None -> retorna None |
| `test_deepgram_inexistente` | deepgram_tts=None, elevenlabs funciona -> retorna audio |
| `test_elevenlabs_inexistente` | elevenlabs=None, deepgram funciona -> retorna audio |
| `test_speed_passado_deepgram` | speed é repassado ao deepgram_tts.generate_speech |
| `test_speed_passado_elevenlabs` | speed é repassado ao elevenlabs.generate_speech (fallback) |
| `test_voice_id_passado_deepgram` | voice_id é repassado ao deepgram_tts.generate_speech |

### 7.2 Testes de Handler (audio.py)

Os testes existentes em `test_audio.py` devem continuar funcionando com alterações mínimas:
- `TestTTSFlow.test_deepgram_tts_used_by_default` → verificar `tts.generate_audio`
- `TestTTSFlow.test_elevenlabs_fallback_when_deepgram_fails` → `mock_tts_orchestrator` com side_effect
- `TestTTSFlow.test_speed_passed_to_deepgram_tts` → verificar kwargs do `generate_audio`
- `TestTTSFlow.test_speed_defaults_to_level_based` → idem

---

## 8. Checklist de Implementação

- [ ] Criar `bot/services/tts_orchestrator.py` com classe `TTSOrchestrator`
- [ ] Atualizar `bot/main.py`: instanciar e registrar `tts_orchestrator` no `bot_data`
- [ ] Atualizar `bot/handlers/audio.py`: substituir bloco duplicado por chamada ao orchestrator
- [ ] Atualizar `bot/handlers/message.py`: idem
- [ ] Atualizar `tests/conftest.py`: adicionar fixture `mock_tts_orchestrator`
- [ ] Atualizar `tests/test_audio.py`: adaptar mocks para usar orchestrator
- [ ] Criar `tests/test_tts_orchestrator.py`: 8 testes unitários
- [ ] Rodar `pytest tests/` — 126+ testes devem continuar passando
- [ ] Code review das alterações
- [ ] Verificar cobertura do novo código

---

## 9. Riscos e Considerações

1. **Ordem dos testes**: `configured_audio_context` fixture precisa incluir `mock_tts_orchestrator` no `bot_data` — isso exige que `mock_tts_orchestrator` seja importado/dependente antes.
2. **Import circular**: `tts_orchestrator.py` importa `DeepgramTTSService` e `ElevenLabsService` — não há risco de ciclo pois esses serviços não importam o orchestrator.
3. **`main.py`**: O `TTSOrchestrator` recebe `None` para serviços não configurados, então o `if config.elevenlabs_api_key` continua necessário, mas o orchestrator gerencia a ausência internamente.
4. **Comportamento preservado**: O orchestrator replica exatamente a lógica atual: Deepgram → ElevenLabs → None, com speed e voice_id.
