# ADR 0001: Deepgram Aura as Primary TTS Provider

## Status

Accepted (2026-05-15)

## Context

The bot needed Text-to-Speech capability for audio responses. Two providers were evaluated:
- **ElevenLabs**: Industry leader in TTS quality, generous free tier (10k chars/month)
- **Deepgram Aura**: Newer TTS offering from Deepgram, lower cost per character

Initially ElevenLabs was selected as primary due to its established reputation and speech quality.

## Decision

After evaluation, Deepgram Aura became the **primary** TTS provider, with ElevenLabs relegated to **fallback** status. Reasons:

1. **Cost**: Deepgram offers significantly lower per-character pricing for TTS
2. **Multiple voices**: Aura provides 4 distinct voices (2F + 2M) out of the box
3. **Single vendor**: Using Deepgram for both STT (nova-2) and TTS simplified API key management
4. **Quality**: Aura's conversational voices (Thalia, Odysseus, Helena, Mars) proved adequate for language learning use cases

ElevenLabs was retained as a fallback when Deepgram generation fails (network issues, rate limits).

## Consequences

- Deepgram TTS handles ~99% of audio generation
- ElevenLabs fallback only activates when Deepgram fails
- Voice selection UI shows only Deepgram voices
- Users can still benefit from ElevenLabs quality when Deepgram has issues (transparent fallback)
