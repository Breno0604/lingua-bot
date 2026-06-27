"""
Teste simples para verificar se a API do Groq esta funcionando.

Uso:
    python tests/test_groq_simple.py

Se funcionar corretamente, voce vera a resposta do Groq no terminal.
Se a API key for invalida, voce vera uma mensagem de erro clara.
"""

import asyncio
import logging
import sys
import os

# Adiciona a raiz do projeto ao path para importar os modulos do bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.config import load_config
from bot.services.groq import GroqService

# Suprime logs do GroqService durante o teste para nao poluir a saida
logging.getLogger("bot.services.groq").setLevel(logging.CRITICAL)


async def test_groq():
    """Testa a conexao com a API do Groq."""

    print("=" * 60)
    print("[TESTE] TESTE DA API GROQ")
    print("=" * 60)

    # Carrega configuracao (le .env automaticamente)
    try:
        config = load_config()
    except ValueError as e:
        print(f"\n[ERRO] Erro de configuracao:\n{e}")
        print("\n[DICA] Verifique se o arquivo .env existe com as variaveis:")
        print("   BOT_TOKEN=...")
        print("   GROQ_API_KEY=...")
        return False

    print(f"\n[INFO] Configuracao carregada:")
    print(f"   Modelo: {config.groq_model}")
    print(f"   API Key: {'[OK] definida' if config.groq_api_key else '[FALTA] nao definida'}")
    print(f"   Tamanho da key: {len(config.groq_api_key)} caracteres")

    if not config.groq_api_key:
        print("\n[ERRO] GROQ_API_KEY nao esta configurada no .env")
        print("[DICA] Gere uma chave em: https://console.groq.com/keys")
        return False

    if config.groq_api_key == "gsk_your_key_here":
        print("\n[ERRO] GROQ_API_KEY ainda e o valor placeholder!")
        print("[DICA] Substitua 'gsk_your_key_here' pela sua chave real do Groq.")
        print("   Gere em: https://console.groq.com/keys")
        return False

    # ================================================================
    # TESTE 1: Chamada direta a API Groq (usando SDK groq)
    # ================================================================
    print(f"\n[AGUARDE] Testando conexao direta com a API Groq...")
    print(f"   Modelo: {config.groq_model}")
    print(f"   Mensagem: 'Hello! How are you?'")

    from groq import Groq as GroqClient

    api_client = GroqClient(api_key=config.groq_api_key)

    try:
        response = await asyncio.to_thread(
            api_client.chat.completions.create,
            model=config.groq_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one word."},
            ],
            max_tokens=10,
            temperature=0.7,
        )
        print(f"\n[OK] API RESPONDEU!\n")
        resposta = response.choices[0].message.content.strip()
        print("-" * 60)
        print(f"Resposta: {resposta}")
        print("-" * 60)
    except Exception as e:
        error_msg = str(e)
        print(f"\n[ERRO] API NAO RESPONDEU:\n")

        if "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
            print("   Motivo: API key invalida!")
            print("\n[DICA] A chave GROQ_API_KEY no seu .env nao e valida.")
            print("   Gere uma nova chave em: https://console.groq.com/keys")
            print("   As chaves do Groq comecam com 'gsk_'")
        elif "404" in error_msg or "not found" in error_msg.lower():
            print(f"   Motivo: Modelo '{config.groq_model}' nao encontrado.")
            print("\n[DICA] Verifique se o nome do modelo esta correto.")
            print("   Lista de modelos: https://console.groq.com/docs/models")
        elif "429" in error_msg or "rate" in error_msg.lower() or "quota" in error_msg.lower():
            print("   Motivo: Limite de requisicoes excedido (rate limit ou quota).")
            print("\n[DICA] Aguarde alguns minutos e tente novamente.")
        else:
            print(f"   {error_msg[:500]}")

        return False

    # ================================================================
    # TESTE 2: Usando o GroqService do projeto (integracao completa)
    # ================================================================
    print(f"\n[AGUARDE] Testando GroqService (integracao completa)...")
    groq_service = GroqService(config)

    try:
        reply = await groq_service.generate_reply(
            conversation_history="",
            user_message="Hello! How are you?"
        )

        if reply:
            print(f"\n[OK] GroqService funcionou!\n")
            print("-" * 60)
            print(f"Resposta: {reply}")
            print("-" * 60)
            print(f"\n[INFO] Estatisticas:")
            print(f"   Tamanho: {len(reply)} caracteres")
            print(f"   Linhas: {reply.count(chr(10)) + 1}")
            return True
        else:
            print(f"\n[ERRO] GroqService retornou None (vazio)")
            return False
    except Exception as e:
        print(f"\n[ERRO] GroqService lancou excecao: {str(e)[:300]}")
        return False


def main():
    """Executa o teste."""
    result = asyncio.run(test_groq())

    print()
    print("=" * 60)
    if result:
        print("[OK] TESTE CONCLUIDO: Groq esta funcionando corretamente!")
    else:
        print("[ERRO] TESTE CONCLUIDO: Groq NAO esta funcionando.")
        print("   Revise as mensagens acima para corrigir o problema.")
    print("=" * 60)

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
