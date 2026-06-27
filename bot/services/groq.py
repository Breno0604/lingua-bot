"""
LinguaBot --- Groq AI Client

Integracao com a API do Groq (OpenAI-compatible).
Fornece:
  - generate_reply(): Gera resposta com base no historico da conversa
  - Retry automatico em caso de falha
  - System prompt configurado para professor de ingles A1-A2
"""

import asyncio
import logging
from typing import Optional

from groq import Groq as GroqClient
from groq.types.chat import ChatCompletion

from bot.config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an enthusiastic and patient English teacher for beginner (A1-A2) students. Your student is a Brazilian Portuguese speaker learning English.

RULES:
1. ALWAYS respond in English only -- full immersion. Never use Portuguese.
2. Use simple vocabulary and short sentences (A1-A2 level).
3. When the student makes a mistake, gently correct:
   - Acknowledge what they got right first
   - Offer the correction with a brief, simple explanation
   - Max 1-2 corrections per message -- don't overwhelm
4. Encourage often -- celebrate their efforts with positive reinforcement.
5. If they use Portuguese, gently redirect to English:
   "Try saying that in English! I know you can do it!"
6. Introduce new relevant vocabulary naturally during conversation.
   When you introduce a new word, format it for vocab extraction:
   NEW_WORD: [word] = [translation]
   EXAMPLE: [simple sentence using the word]
7. Keep responses conversational, engaging, and varied.
8. Tone: balanced -- friendly and encouraging like a friend, but with teacher-like clarity when correcting mistakes.
9. Keep your responses relatively short (2-4 sentences) for beginners."""


class GroqService:
    """Cliente para a API do Groq com retry automatico."""

    def __init__(self, config: Config):
        self.api_key = config.groq_api_key
        self.model = config.groq_model
        self.max_retries = 2
        self.retry_delay = 2  # segundos
        self._client: Optional[GroqClient] = None

    def _get_client(self) -> GroqClient:
        """Retorna (ou cria) o cliente Groq."""
        if self._client is None:
            self._client = GroqClient(api_key=self.api_key)
        return self._client

    async def generate_reply(
        self, conversation_history: str, user_message: str
    ) -> Optional[str]:
        """
        Gera uma resposta do Groq com base no historico e na mensagem do usuario.

        Args:
            conversation_history: Historico formatado da conversa.
                OBS: O historico ja inclui a mensagem atual do usuario
                (adicionada via add_user_message() antes de get_formatted_history()).
            user_message: Mensagem atual do usuario (usada apenas como fallback
                quando nao ha historico).

        Returns:
            Texto da resposta, ou None se todas as tentativas falharem.
        """
        messages = self._build_messages(conversation_history, user_message)

        for attempt in range(1, self.max_retries + 2):  # tentativa inicial + retries
            try:
                loop = asyncio.get_running_loop()
                response: ChatCompletion = await loop.run_in_executor(
                    None,
                    self._sync_generate,
                    messages,
                )
                if response and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        return content.strip()
                    else:
                        logger.warning("Groq retornou resposta vazia")
                        return None
                else:
                    logger.warning("Groq retornou resposta sem choices")
                    return None

            except Exception as e:
                logger.error(
                    "Erro ao chamar Groq (tentativa %d/%d): %s",
                    attempt,
                    self.max_retries + 1,
                    str(e),
                )

                if attempt <= self.max_retries:
                    logger.info("Tentando novamente em %d segundos...", self.retry_delay)
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("Todas as tentativas de chamar Groq falharam")
                    return None

        return None

    def _sync_generate(self, messages: list[dict]) -> ChatCompletion:
        """Chamada sincrona ao Groq (executada em thread separada)."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=400,
        )
        return response

    def _build_messages(self, conversation_history: str, user_message: str) -> list[dict]:
        """Constroi a lista de mensagens no formato ChatML.

        O conversation_history pode conter o historico completo da conversa.
        O user_message e SEMPRE adicionado como ultima mensagem do usuario,
        garantindo que a acao/instrucao atual chegue ao modelo.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        if conversation_history:
            # Formato esperado: "Teacher: ...\nStudent: ...\nTeacher: ..."
            for line in conversation_history.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Teacher:"):
                    messages.append({"role": "assistant", "content": line[len("Teacher:"):].strip()})
                elif line.startswith("Student:"):
                    messages.append({"role": "user", "content": line[len("Student:"):].strip()})

        # Sempre adiciona a mensagem/instrucao atual como ultima msg do usuario
        messages.append({"role": "user", "content": user_message})

        return messages
