# Spec: Melhoria da Qualidade das Respostas

**Data:** 2026-07-17
**Status:** Aprovado
**Abordagem:** Prompt + Parâmetros (Equilibrado)

---

## 1. Problema

As respostas do LinguaBot apresentam 4 problemas principais:

1. **Genéricas/repetitivas** — Respostas seguem padrão previsível, sem variação
2. **Perdem contexto** — Bot não referencia o que foi dito antes na conversa
3. **Correções ruins** — Correções vagas ("almost there") sem explicar o erro
4. **Nível inadequado** — Vocabulário e estrutura não condizem com nível do aluno

---

## 2. Solução

### 2.1 System Prompts Melhorados

#### Few-shot examples por nível

Cada prompt terá 2-3 exemplos concretos de conversa mostrando formato ideal.

**Exemplo A1:**
```
STUDENT: I eated pizza yesterday
TEACHER: Almost! We say "ate", not "eated". "Ate" is the past of "eat". 
Great try though! Do you like pizza? Yes or no?

STUDENT: yes i like pizza
TEACHER: Awesome! Pizza is delicious!
NEW_WORD: delicious = delicioso
EXAMPLE: This pizza is delicious!
What other food do you like?
```

#### Regras anti-repetição

```
STRUCTURE RULES:
- Never start 2 consecutive responses the same way
- Vary sentence openings: [Great!, Nice!, I see!, Good!, Interesting!]
- Alternate: short response → long response → short response
- Don't always end with a question
```

#### Regras de correção específicas

| Nível | Regra |
|-------|-------|
| A1 | Corrija APENAS 1 erro por mensagem. Explique em 1 frase simples. |
| A2 | Corrija 1-2 erros. Use exemplo prático de como deveria ser. |
| B1 | Model the correct form naturally. Suggest more natural alternatives. |

#### Contexto da conversa

Incluir instrução explícita no system prompt:
```
Continue the conversation naturally. Reference what the student said before.
Do not start fresh each time — build on the context.
```

---

### 2.2 Parâmetros do Modelo

#### Configuração por nível

| Nível | temperature | top_p | max_tokens | justificativa |
|-------|-------------|-------|------------|---------------|
| A1 | 0.5 | 0.9 | 200 | Respostas curtas e previsíveis |
| A2 | 0.7 | 0.95 | 300 | Equilíbrio entre criatividade e consistência |
| B1 | 0.8 | 0.95 | 400 | Mais liberdade criativa, respostas maiores |

#### Penalidades

| Parâmetro | Valor | Efeito |
|-----------|-------|--------|
| `frequency_penalty` | 0.3 | Reduz repetição de palavras |
| `presence_penalty` | 0.2 | Incentiva tópicos novos |

#### Implementação

```python
LEVEL_PARAMS = {
    "A1": {"temperature": 0.5, "top_p": 0.9, "max_tokens": 200},
    "A2": {"temperature": 0.7, "top_p": 0.95, "max_tokens": 300},
    "B1": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 400},
}
```

---

### 2.3 Validação Pós-Geração

#### Critérios por nível

| Nível | Regra | Critério |
|-------|-------|----------|
| A1 | Comprimento | Máx 25 palavras |
| A1 | Vocabulário | Apenas 800 palavras mais comuns (lista estática em `data/top_800_words.txt`) |
| A2 | Comprimento | Máx 30 palavras |
| A2 | Vocabulário | Evitar idioms complexos (lista em `data/idioms_to_avoid.txt`) |
| B1 | Comprimento | Máx 35 palavras |
| B1 | Vocabulário | Livre (inclui phrasal verbs) |

#### Scoring

Score = (peso_comprimento + peso_vocabulario + peso_estrutura) / 3

| Componente | Peso | Critério |
|------------|------|----------|
| Comprimento | 0.4 | Dentro do limite = 1.0, fora = 0.0 |
| Vocabulário | 0.4 | Adequado ao nível = 1.0, inadequado = 0.0 |
| Estrutura | 0.2 | Formato correto = 1.0, incorreto = 0.0 |

#### Retry inteligente

Se `score < 0.6`:
1. Adicionar nota ao prompt: "Note: Your previous response violated level rules. [issues]"
2. Retry com `temperature - 0.1` (mais conservador)
3. Máximo 1 retry — se falhar novamente, usar resposta original

---

### 2.4 Estrutura e Consistência

#### Formato padronizado

| Nível | Estrutura | Exemplo |
|-------|-----------|---------|
| A1 | Elogio curto + resposta + pergunta simples | "Great! I like cats too. Do you like dogs?" |
| A2 | Contexto + resposta + pergunta wh- | "That's interesting! I went to the store yesterday. Where did you go?" |
| B1 | Resposta elaborada + pergunta aberta | "I understand what you mean. Many people feel that way. What do you think about it?" |

#### Regras de emojis

| Nível | Regra |
|-------|-------|
| A1 | Máx 1 emoji por resposta |
| A2 | Máx 2 emojis por resposta |
| B1 | Apenas para ênfase (1-2 no máximo) |

#### Normalização de vocabulário

Formato fixo para todas as respostas:
```
NEW_WORD: [palavra] = [tradução]
EXAMPLE: [frase simples usando a palavra]
```

---

## 3. Implementação

### 3.1 Arquivos afetados

| Arquivo | Mudança |
|---------|---------|
| `bot/services/groq.py` | System prompts + parâmetros por nível + retry |
| `bot/services/response_validator.py` | **NOVO** — Validação pós-geração |
| `tests/test_groq.py` | +5-8 testes para parâmetros |
| `tests/test_response_validator.py` | **NOVO** — 15-20 testes |
| `tests/test_integration.py` | **NOVO** — 5-8 testes de integração |

### 3.2 Ordem de implementação

1. System prompts (few-shot + regras anti-repetição)
2. Parâmetros por nível em `groq.py`
3. `response_validator.py`
4. Testes unitários
5. Testes de integração
6. Ajustes finais baseados em testes manuais

---

## 4. Métricas de Sucesso

| Métrica | Antes | Depois |
|---------|-------|--------|
| Respostas repetitivas | ~40% | <15% |
| Correções claras | ~50% | >85% |
| Nível adequado | ~60% | >90% |
| Testes passando | 206 | 230+ |
