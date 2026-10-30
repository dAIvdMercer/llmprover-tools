# Model Compare

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compare/compare.ipynb)

Fire **one prompt at two models** you name, using **your own API keys**, and see their responses,
token cost, and latency **side by side**. 60 seconds, free, no signup. Model-agnostic: it compares
whatever models your key reaches, this year or next.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.com).

## Run it

Three ways, lowest friction first.

### (a) Open in Colab (zero install)

Click the badge above. Paste your keys into a cell, set your two models and prompt, run. The
notebook is the primary run path if you do not want to install anything.

### (b) One-shot with uvx / pipx

```bash
uvx llmprover-compare --models gpt-5,claude-opus-5-5 --prompt "Explain CRDTs in one sentence."
# or:  pipx run llmprover-compare --models ...
```

### (c) Clone and run

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/compare
pip install -r requirements.txt        # or: pip install -e .

export OPENAI_API_KEY=sk-...           # set the env vars your two models need
export ANTHROPIC_API_KEY=sk-ant-...

python compare.py --models gpt-5,claude-opus-5-5 --prompt "Explain CRDTs in one sentence."
```

Key env vars by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`,
`TOGETHER_API_KEY`, `GROQ_API_KEY`. Provider is inferred from the model id (e.g. `gpt-*` -> OpenAI,
`claude*` -> Anthropic, `gemini*` -> Google, `grok*` -> xAI, `qwen/*` -> Groq, `<org>/<model>` -> Together).

## What it does, and what it does not

**Does (free):** two models, one prompt, each response + token cost + latency, side by side. That
is the whole job, done well. Cost comes from a stamped static snapshot (`prices.json`), not a live
feed, so the tool never phones home.

**Does not (by design):** it is a **head-to-head** (exactly two models) and it emits **no verdict**:
no score, no winner, no quality hint. You eyeball the two responses yourself.

When you want to compare 5-20 at once, score which is best, see which layer broke, track drift over
time, or put any of this inside your agent, that is [LLM Prover](https://llmprover.com).

## Your keys stay on your machine

Keys are read from your environment (or pasted into a Colab cell on your own machine) and used to
call the **provider's API directly**. **They are never sent to pysolvr.** You are responsible for
your own usage and costs.

**Do not commit your keys.** This repo's `.gitignore` excludes `.env` and secret files, but run a
secret scan before pushing (e.g. `gitleaks detect --source . --no-git`) and rotate any key that
ever lands in a commit. See the repo root README for the full note.

## Prices drift

`prices.json` is a dated snapshot (`prices_as_of`), not a live feed. Edit it locally for models it
does not list. For the live, authoritative table see **https://llmprover.com/api-pricing/**.

## Legal

Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage
and costs. Keys never leave your machine and are never sent to pysolvr. Outputs are informational,
not advice. pysolvr is not liable for decisions made from these results.
