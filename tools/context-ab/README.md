# Context A/B Tester

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/context-ab/context_ab.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/context-ab/context_ab.ipynb)

**See how the context you give an AI changes its answer.** Ask one question of one model two ways,
side by side:
- **with vs without** your document \u2014 ask it cold, then ask it again with your policy/doc pasted in,
  and watch the answer become correct. The clearest demonstration of *why grounding matters*.
- **context A vs context B** \u2014 same question, two different documents (e.g. an old policy vs a new one).

About a minute, free, no signup. Works with whatever model your key can reach.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute \u2014 no install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/context-ab/context_ab.ipynb)
2. **Run each grey box top to bottom** with its play (\u25b6) button.
3. The page walks you through adding your API key safely, choosing a model, and pasting your question
   and your document. The last step shows the two answers side by side.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key** \u2014 a password-like string you get from the provider's website. The cost of each run is
yours (usually a fraction of a cent). You only need **one** provider's key (this tool runs a single
model).

| Provider | Where to get a key | Powers models like |
|----------|--------------------|--------------------|
| OpenAI | platform.openai.com \u2192 API keys | `gpt-5`, `gpt-4o` |
| Anthropic | console.anthropic.com \u2192 API keys | `claude-opus-5-5` |
| Google (Gemini) | aistudio.google.com \u2192 Get API key | `gemini-4-argon` |

**Your key stays with you** \u2014 it is never sent to pysolvr. Not sure what models exist or cost? See
[llmprover.pysolvr.com/models](https://llmprover.pysolvr.com/models/) and
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

## Run it in a terminal (for developers)

Keys are read from environment variables \u2014 never from a flag or a file in the repo.

```bash
export OPENAI_API_KEY=sk-...

# with vs without context (default):
uvx llmprover-context-ab --model gpt-5 \
    --question "Can I expense a 1,200 USD laptop without approval?" \
    --context-file policy.txt

# context A vs context B:
uvx llmprover-context-ab --model gpt-5 --mode a-b \
    --question "What is the refund window?" \
    --context-a-file policy_v1.txt --context-b-file policy_v2.txt
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/context-ab
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python context_ab.py --model gpt-5 --question "..." --context "paste or --context-file"
```

Key environment variables by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`. The provider is inferred from the model id.

## What it does, and what it does not

**Does (free):** one model, one question, answered two ways (with/without context, or A/B), each
answer + token cost + latency, side by side. The "context" is text you paste \u2014 prepended to your
question as grounding (how most people actually use context). No embeddings, no vector store.

**Does not (by design):** it shows both answers; it gives **no verdict** \u2014 it does not *score* which
answer is more grounded, correct, or faithful, and it does not tell you *which layer* broke. You read
the two answers and judge for yourself.

When you want scored grounding across a whole document store (thousands of docs, retrieved at scale),
the which-layer diagnostic, and drift tracking over time, that is
[LLM Prover](https://llmprover.pysolvr.com/rag-evaluation/).

## Your keys stay with you

Your API key is read from your environment (or Google Colab's encrypted Secrets panel) and used to
call the provider directly. **It is never sent to pysolvr.** You are responsible for your own usage
and costs. If you edit and save your own copy, never put a key in a file you share or commit; if a
key ends up somewhere public, delete it at the provider and create a new one ("rotate" it).

## Prices drift

`prices.json` is a dated snapshot (`prices_as_of`), not a live feed. For the current table see
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

## Legal

Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine (or your Colab account) and are never sent to pysolvr. Outputs
are informational, not advice. pysolvr is not liable for decisions made from these results.
