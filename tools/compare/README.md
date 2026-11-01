# Model Compare

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compare/compare.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compare/compare.ipynb)

Fire **one prompt at two AI models** you choose, using **your own API keys**, and see their answers,
cost, and speed **side by side**. About a minute, free, no signup. It works with whatever models your
key can reach, so it never goes out of date.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

You can run this in your browser with **Google Colab** in about a minute. You do not need to install
anything or know how to code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compare/compare.ipynb)
   It opens the tool in your browser (a free Google account is all you need).
2. **Follow the numbered steps in the page.** Each grey box is a step: click the little
   **play (▶) button** on the left of a box to run it, top to bottom.
3. The page walks you through adding your API keys safely, choosing two models, and typing your
   question. The last step shows the two answers side by side.

That is the whole thing. The rest of this page is for people who prefer a terminal.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider (OpenAI,
Anthropic, Google, etc.), so the answers are real and the cost is yours (usually a fraction of a
cent per run).

An **API key** is a password-like string that lets the tool use your account with one of those
providers. You get one from the provider's website. For example:

| Provider | Where to get a key | Powers models like |
|----------|--------------------|--------------------|
| OpenAI | platform.openai.com → API keys | `gpt-5`, `gpt-4o` |
| Anthropic | console.anthropic.com → API keys | `claude-opus-5-5` |
| Google (Gemini) | aistudio.google.com → Get API key | `gemini-4-argon` |

You need a key for **each** provider whose model you want to compare (so for "GPT vs Claude", you
need an OpenAI key and an Anthropic key). Most providers require a small amount of prepaid credit.
**Your key stays with you** — it is never sent to pysolvr (see "Your keys stay with you" below).

Not sure which models exist or what they cost? See **[llmprover.pysolvr.com/models](https://llmprover.pysolvr.com/models/)**
and **[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/)**.

## Run it in a terminal (for developers)

Two ways. Both read your keys from environment variables — never from a file in the repo.

### One-shot with uvx / pipx (no install)

```bash
export OPENAI_API_KEY=sk-...            # set keys for the two providers you're comparing
export ANTHROPIC_API_KEY=sk-ant-...

uvx llmprover-compare --models gpt-5,claude-opus-5-5 --prompt "Explain CRDTs in one sentence."
# or:  pipx run llmprover-compare --models gpt-5,claude-opus-5-5 --prompt "..."
```

### Clone and run

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/compare
pip install -r requirements.txt

export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

python compare.py --models gpt-5,claude-opus-5-5 --prompt "Explain CRDTs in one sentence."
```

Key environment variables by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`. The provider is inferred from the model id
(`gpt-*` → OpenAI, `claude*` → Anthropic, `gemini*` → Google, `grok*` → xAI, `qwen/*` → Groq,
`<org>/<model>` → Together).

## What it does, and what it does not

**Does (free):** two models, one prompt, each answer + token cost + speed, side by side. That is the
whole job, done well. Cost is computed from a dated price snapshot (`prices.json`), not a live feed,
so the tool never calls home.

**Does not (by design):** it is a **head-to-head** (exactly two models) and it gives **no verdict** —
no score, no winner, no "which is better". You read the two answers and judge for yourself.

When you want to compare 5-20 models at once, score which is best, see *which layer* broke, track
drift over time, or run this inside an AI agent, that is [LLM Prover](https://llmprover.pysolvr.com/?tool=compare).

## Your keys stay with you

Your API keys are read from your environment (or from Google Colab's encrypted Secrets panel when you
run it there) and used to call the **provider directly**. **They are never sent to pysolvr.** You are
responsible for your own usage and the cost on your provider account.

If you edit and save your own copy of this code, do not put a key directly in a file you share or
commit. If a key ever does end up somewhere public, delete it and create a new one at the provider
(this is called "rotating" the key).

## Prices drift

`prices.json` is a dated snapshot (`prices_as_of`), not a live feed. You can edit it locally for any
model it does not list. For the current, authoritative table see
**[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/)**.

## Legal

Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine (or your Colab account) and are never sent to pysolvr. Outputs
are informational, not advice. pysolvr is not liable for decisions made from these results.
