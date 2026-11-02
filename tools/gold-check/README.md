# Gold-Standard Verification

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/gold-check/gold_check.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/gold-check/gold_check.ipynb)

**You know the right answer, did the AI get it?** Bring a question, a known-correct reference answer
(your "gold standard"), and a model with your own key. The tool asks the model, then runs a
single-pass check comparing its answer to your gold standard, and tells you whether it **matches**,
**partially matches**, or **does not match**, with a short comment on what differs.

About a minute, free, no signup. Works with whatever model your key can reach.

> **This is a basic first-look check, not verification you can rely on professionally.** It uses a
> single AI judge with a stock prompt, no rubric, no consistency check, no audit trail. A single AI
> judge can be inconsistent and can flip its result on a re-run. If your profession requires you to
> verify AI output (legal, tax, medical, accounting, and others), **this tool does not discharge that
> duty.** It is a first look, not a certification. Every run prints this reminder.

It comes **pre-filled with a demonstration default** so your first run shows the check *running* and
commenting on a real example. The point is to watch the mechanism work, not to watch it pass.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/gold-check/gold_check.ipynb)
2. **Run each grey box top to bottom** with its play (>) button. The first run uses the pre-filled
   demonstration so you can watch the check run.
3. The page walks you through adding your API key safely. Then overwrite the question, the gold
   standard, and the model with your own and re-run.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key**, a password-like string you get from the provider's website. Each run makes two calls
(the answer, then the check), each a fraction of a cent. You only need **one** provider's key if the
answering model and the checking model are from the same provider.

| Provider | Where to get a key | Powers models like |
|----------|--------------------|--------------------|
| OpenAI | platform.openai.com, API keys | `gpt-5`, `gpt-4o` |
| Anthropic | console.anthropic.com, API keys | `claude-opus-5-5` |
| Google (Gemini) | aistudio.google.com, Get API key | `gemini-4-argon` |

**Your key stays with you.** It is never sent to pysolvr. Not sure what models exist or cost? See
[llmprover.pysolvr.com/models](https://llmprover.pysolvr.com/models/) and
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

## Run it in a terminal (for developers)

Keys are read from environment variables, never from a flag or a file in the repo.

```bash
export OPENAI_API_KEY=sk-...

# run the demonstration default (watch the check run):
uvx llmprover-gold-check

# your own:
uvx llmprover-gold-check --model gpt-5 \
    --question "In how many days must a customer request a refund?" \
    --reference "Within 14 days of delivery; later requests are not eligible." \
    --judge-model gpt-5
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/gold-check
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python gold_check.py   # runs the demo default
```

Use `--reference-file` to load a longer gold standard from a file, and `--judge-model` to use a
different model for the check than for the answer. Key environment variables by provider:
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY`,
`GROQ_API_KEY`. The provider is inferred from the model id.

## What it does, and what it does not

**Does (free):** asks the model your question, then runs one checking pass (a second model call with
a stock prompt) comparing the answer to your gold standard, and reports match / partial / mismatch
with a short comment and the cost.

**Does not (by design):** it is a **single-pass check with no rubric, no consistency check, and no
audit trail**. It is a first look, not professional verification, and it can be wrong or inconsistent.
It does not certify anything and does not discharge any professional duty to verify AI output.

Verification you can rely on, rubric-based scoring, running the judge several times to confirm it is
consistent, an audit trail, and checking against your whole regulation or policy corpus, is
[LLM Prover](https://llmprover.pysolvr.com/?tool=gold-check). Background on why a single pass is not
enough: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

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
costs. Keys never leave your machine (or your Colab account) and are never sent to pysolvr. This is a
basic single-pass check, not professional verification, and not legal, medical, tax, or other advice.
You remain responsible for independently verifying AI output as your profession or situation requires.
pysolvr is not liable for decisions made from these results.
