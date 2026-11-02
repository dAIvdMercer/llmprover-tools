# Right-Size It

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/right-size/right_size.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/right-size/right_size.ipynb)

**Find the cheapest model that is still good enough for your task.** Run one prompt across a few
models with your own key, read the answers, mark which ones are good enough, and the tool tells you
the cheapest of the ones **you** accepted, and how much it saves versus the priciest one you accepted.
On many everyday tasks a cheap model matches a flagship, and the flagship can cost a hundred times as
much for the same result.

About a minute, free, no signup. Works with whatever models your key can reach.

**You make the quality call. The tool only adds up cost.** It never decides which answer is good
enough, that is yours. It comes **pre-filled with a demonstration default** (a simple task across a
cheap, a mid, and a flagship model, with an example "all three acceptable" selection), so your first
run already shows the point: the cheapest acceptable saves most of the cost for a task even a cheap
model handles.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/right-size/right_size.ipynb)
2. **Run each grey box top to bottom** with its play (>) button. The first run uses the pre-filled
   demonstration.
3. The page walks you through adding your API keys safely. Then overwrite the prompt and models with
   your own, read the answers, mark the good-enough ones, and re-run the last cell.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with each AI provider via an
**API key**, a password-like string you get from the provider's website. Each run costs a fraction
of a cent. You need a key for **each** provider whose model you include.

| Provider | Where to get a key | Powers models like |
|----------|--------------------|--------------------|
| OpenAI | platform.openai.com, API keys | `gpt-5`, `gpt-4o`, `gpt-4o-mini` |
| Anthropic | console.anthropic.com, API keys | `claude-opus-5-5` |
| Google (Gemini) | aistudio.google.com, Get API key | `gemini-4-argon` |

**Your keys stay with you.** They are never sent to pysolvr. Not sure what models exist or cost? See
[llmprover.pysolvr.com/models](https://llmprover.pysolvr.com/models/) and
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

## Run it in a terminal (for developers)

Keys are read from environment variables, never from a flag or a file in the repo.

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# run the demonstration default (simple task, example marks pre-filled):
uvx llmprover-right-size

# your own: run across your models, read the answers, then re-run with your picks:
uvx llmprover-right-size --models gpt-4o-mini,gpt-4o,claude-opus-5-5 \
    --prompt "Classify this ticket as billing/technical/other: ..."
# ... read the numbered answers, then:
uvx llmprover-right-size --models gpt-4o-mini,gpt-4o,claude-opus-5-5 \
    --prompt "Classify this ticket as billing/technical/other: ..." --acceptable 1,2
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/right-size
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python right_size.py   # runs the demo default
```

Give 2 to 6 models. Omit `--acceptable` to print the answers and stop; re-run with `--acceptable`
and the run numbers you judge good enough. Key environment variables by provider: `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`.

## What it does, and what it does not

**Does (free):** runs one prompt across 2 to 6 models, shows each answer with its cost, and, once
**you** mark which answers are good enough, names the cheapest of those and the saving versus the
most expensive one you accepted. Cost comes from a dated price snapshot.

**Does not (by design):** it **does not judge quality**. It never decides which answer is good
enough, you do, by eye, for your own task. The tool only does cost arithmetic over your marks. The
automated version, a judge that scores which models clear your quality bar and picks the cheapest
across your whole workload, plus the which-layer diagnostic and drift tracking, is
[LLM Prover](https://llmprover.pysolvr.com/?tool=right-size). Background on paying for only the
quality you need: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

## Your keys stay with you

Your API keys are read from your environment (or Google Colab's encrypted Secrets panel) and used to
call the providers directly. **They are never sent to pysolvr.** You are responsible for your own
usage and costs. If you edit and save your own copy, never put a key in a file you share or commit;
if a key ends up somewhere public, delete it at the provider and create a new one ("rotate" it).

## Prices drift

`prices.json` is a dated snapshot (`prices_as_of`), not a live feed. For the current table see
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

## Legal

Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine (or your Colab account) and are never sent to pysolvr. You decide
which answers are good enough; the tool only adds up cost. Outputs are informational, not advice.
pysolvr is not liable for decisions made from these results.
