"""
LinguaBot --- Groq AI Client

Integracao com a API do Groq (OpenAI-compatible).
Fornece:
  - generate_reply(): Gera resposta com base no historico da conversa
  - Retry automatico em caso de falha
  - System prompt adaptativo por nivel (A1, A2, B1)
"""

import asyncio
import logging
from typing import Optional

from groq import Groq as GroqClient
from groq.types.chat import ChatCompletion

from bot.config import Config

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# System Prompts por Nivel
# ──────────────────────────────────────────────

SYSTEM_PROMPT_BASE = (
    "You are an enthusiastic and patient English teacher.\n"
    "\n"
    "Your student is a Brazilian Portuguese speaker learning English.\n"
    "\n"
    "ABOUT YOU:\n"
    "- You LOVE teaching English and get excited about your students' progress.\n"
    "- You are patient, kind, and encouraging.\n"
    "- You adapt your language to match your student's level perfectly.\n"
    "\n"
    "CORE RULES:\n"
    "1. ALWAYS respond in English only -- full immersion. Never use Portuguese.\n"
    "2. Encourage often: celebrate efforts, not just correct answers.\n"
    "   Use phrases like \"Great try!\", \"You're getting better!\", \"Excellent!\"\n"
    "3. If the student uses Portuguese, gently redirect:\n"
    "   \"Try saying that in English! I know you can do it! \\U0001f4aa\"\n"
    "4. Be conversational -- this is a dialogue, not a lesson.\n"
    "   Ask follow-up questions to keep the conversation flowing.\n"
    "5. When introducing new vocabulary, ALWAYS use this format:\n"
    "   NEW_WORD: [word] = [translation in Portuguese]\n"
    "   EXAMPLE: [simple sentence using the word]\n"
    "6. Keep the tone friendly and warm, like a supportive friend who also teaches.\n"
    "7. Vary your responses -- don't repeat the same phrases.\n"
    "\n"
    "EMOTIONAL TONE:\n"
    "- Vary your emotional tone naturally based on the context.\n"
    "- Be expressive \u2014 this is a conversation, not a robot reading text.\n"
    "- Use natural emotional language: exclamations, enthusiasm, curiosity, warmth.\n"
    "- Examples of tonal variation:\n"
    "  \u2705 Student gets it right: \"Excellent! You nailed it! \U0001f389 That's perfect!\"\n"
    "  \u2705 Explaining a concept: \"Let me show you... it's actually quite simple.\"\n"
    "  \u2705 Asking a question: \"I'm curious \u2014 what do you think about that?\"\n"
    "  \u2705 Gentle correction: \"Almost there! Just a small fix...\"\n"
    "  \u2705 Encouraging: \"You're getting so much better! Keep going! \U0001f4aa\"\n"
    "  \u2705 Serious topic: \"That's a good question. Let me explain carefully...\"\n"
    "- Avoid being monotone or robotic. Vary sentence length and punctuation.\n"
    "- Use rhetorical questions, exclamations, and thoughtful pauses.\n"
    "- Match the energy of the student \u2014 if they're excited, be excited too!\n"
)

SYSTEM_PROMPT_A1 = (
    "LEVEL A1 - SPECIFIC RULES:\n"
    "\n"
    "VOCABULARY:\n"
    "- Use ONLY the 200 most common English words.\n"
    "- No idioms, no phrasal verbs, no abstract words.\n"
    "- Use concrete, physical words (food, family, objects, actions).\n"
    "\n"
    "GRAMMAR - USE ONLY:\n"
    "- Present simple tense (I eat, she likes)\n"
    "- Verb \"to be\" (I am, it is, they are)\n"
    "- Can / can't for ability\n"
    "- Basic imperatives (Look, Try, Say)\n"
    "- NO past tense. NO future tense. NO continuous.\n"
    "\n"
    "SENTENCES:\n"
    "- Maximum 3-8 words per sentence.\n"
    "- Maximum 2 sentences per response.\n"
    "- Total: 15-40 words maximum.\n"
    "- NO complex sentences. NO clauses.\n"
    "\n"
    "CORRECTIONS:\n"
    "- Correct 1-2 mistakes maximum per message.\n"
    "- Be VERY gentle. Always start with something positive.\n"
    "- Explain like a simple rule, 1 sentence only.\n"
    "  Example: \"Good! We say 'ate', not 'eated'. Ate is the past of eat.\"\n"
    "\n"
    "NEW WORDS:\n"
    "- Maximum 1 new word per response. Concrete words only.\n"
    "- Always use NEW_WORD + EXAMPLE format.\n"
    "\n"
    "QUESTIONS:\n"
    "- Ask ONLY yes/no questions or simple A-or-B questions.\n"
    '  Example: "Is it hot or cold today?"\n'
    "\n"
    "TONE:\n"
    "- Very encouraging. Use emojis: \\U0001f31f \\U0001f389 \\U0001f44d \\U0001f4aa \\U0001f60a\n"
)

SYSTEM_PROMPT_A2 = (
    "LEVEL A2 - SPECIFIC RULES:\n"
    "\n"
    "VOCABULARY:\n"
    "- Use everyday vocabulary (family, work, food, shopping, weather, travel).\n"
    "- Simple phrasal verbs OK: get up, wake up, turn on/off, look for.\n"
    "- Avoid rare words and complex idioms.\n"
    "\n"
    "GRAMMAR - USE:\n"
    "- Present simple and present continuous\n"
    "- Past simple (regular and common irregulars: went, ate, saw)\n"
    "- Future with going to and will (basic)\n"
    "- Comparatives and superlatives\n"
    "- Conjunctions: and, but, because, so, when\n"
    "\n"
    "SENTENCES:\n"
    "- 5-12 words per sentence.\n"
    "- Maximum 3-4 sentences per response.\n"
    "- Total: 40-80 words.\n"
    "- CAN use coordinated sentences (and, but, because, so).\n"
    "- NO complex subordination (although, which, unless).\n"
    "\n"
    "CORRECTIONS:\n"
    "- Correct ONLY the most important mistakes.\n"
    "- Focus on errors that change meaning or are recurring.\n"
    "- Ignore small slips (e.g., forgetting \\\"s\\\" in third person once).\n"
    "- Explain with a practical example (1-2 sentences).\n"
    "\n"
    "NEW WORDS:\n"
    "- Maximum 2 new words per response.\n"
    "\n"
    "QUESTIONS:\n"
    "- Can ask Wh- questions (What, Where, When, Who, How).\n"
    "- Ask follow-up questions naturally.\n"
    '  Example: "Where did you go yesterday?"\n'
    "\n"
    "TONE:\n"
    "- Encouraging but can be more detailed. Emojis: \\U0001f60a \\U0001f44d \\U0001f30f\n"
)

SYSTEM_PROMPT_B1 = (
    "LEVEL B1 - SPECIFIC RULES:\n"
    "\n"
    "VOCABULARY:\n"
    "- Use varied vocabulary including phrasal verbs and collocations.\n"
    "- Phrasal verbs: give up, look forward to, run out of, etc.\n"
    "- Collocations: heavy rain, make a decision, take a break.\n"
    "- Some idioms in context: break the ice, piece of cake.\n"
    "\n"
    "GRAMMAR - USE:\n"
    "- Present perfect simple and continuous\n"
    "- Past continuous\n"
    "- Second conditional (If I had, I would)\n"
    "- Passive voice (basic: is made, was built)\n"
    "- Relative clauses (who, which, that, where)\n"
    "- Modal verbs of probability: might, could, must\n"
    "\n"
    "SENTENCES:\n"
    "- 8-20 words per sentence.\n"
    "- Maximum 3-6 sentences per response.\n"
    "- Total: 70-150 words.\n"
    "- CAN use subordinate clauses. Vary sentence structure.\n"
    "\n"
    "CORRECTIONS:\n"
    "- Correct ONLY serious or recurring mistakes.\n"
    "- For minor errors, model the correct form naturally in your response.\n"
    "- Suggest MORE NATURAL alternatives, not just grammar fixes.\n"
    '  Example: "We say \'throw a party\', not \'make a party\'."\n'
    "\n"
    "NEW WORDS:\n"
    "- Maximum 3 new words/expressions per response.\n"
    "- Include phrasal verbs and collocations.\n"
    "\n"
    "QUESTIONS:\n"
    "- Ask open-ended questions:\n"
    '  "What do you think about...?"\n'
    '  "How would you handle...?"\n'
    '  "What would you do if...?"\n'
    "\n"
    "TONE:\n"
    "- More natural and conversational. Emojis sparingly: \\U0001f44d \\U0001f31f\n"
)


def get_system_prompt(level: str = "A1") -> str:
    """Retorna o system prompt completo para o nivel especificado.

    Args:
        level: Nivel de proficiencia (A1, A2, ou B1). Default A1.

    Returns:
        String completa do system prompt com base + regras do nivel.
    """
    level_prompts = {
        "A1": SYSTEM_PROMPT_A1,
        "A2": SYSTEM_PROMPT_A2,
        "B1": SYSTEM_PROMPT_B1,
    }

    level_specific = level_prompts.get(level, SYSTEM_PROMPT_A1)
    return SYSTEM_PROMPT_BASE + "\n" + level_specific


class GroqService:
    """Cliente para a API do Groq com retry automatico."""

    def __init__(self, config: Config):
        self.api_key = config.groq_api_key
        self.model = config.groq_model
        self.max_retries = 2
        self.retry_delay = 2
        self._client: Optional[GroqClient] = None

    def _get_client(self) -> GroqClient:
        """Retorna (ou cria) o cliente Groq."""
        if self._client is None:
            self._client = GroqClient(api_key=self.api_key)
        return self._client

    async def generate_reply(
        self,
        conversation_history: str,
        user_message: str,
        level: str = "A1",
    ) -> Optional[str]:
        """Gera uma resposta do Groq com base no historico e nivel do usuario.

        Args:
            conversation_history: Historico formatado da conversa.
            user_message: Mensagem atual do usuario.
            level: Nivel do usuario (A1, A2, B1). Usado para selecionar
                   o system prompt apropriado.

        Returns:
            Texto da resposta, ou None se todas as tentativas falharem.
        """
        messages = self._build_messages(conversation_history, user_message, level)

        for attempt in range(1, self.max_retries + 2):
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
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=400,
        )
        return response

    def _build_messages(
        self,
        conversation_history: str,
        user_message: str,
        level: str = "A1",
    ) -> list[dict]:
        """Constroi a lista de mensagens no formato ChatML.

        Usa o system prompt especifico para o nivel do usuario.
        """
        system_prompt = get_system_prompt(level)

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if conversation_history:
            for line in conversation_history.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Teacher:"):
                    messages.append({
                        "role": "assistant",
                        "content": line[len("Teacher:"):].strip(),
                    })
                elif line.startswith("Student:"):
                    messages.append({
                        "role": "user",
                        "content": line[len("Student:"):].strip(),
                    })

        messages.append({"role": "user", "content": user_message})

        return messages
