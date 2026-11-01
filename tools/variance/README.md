# Variance Tester

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/variance/variance.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/variance/variance.ipynb)

**How consistent is this model, really?** Ask one model the same prompt several times and see how
much the answer moves. You get every response side by side, their token cost and latency, and a
mechanical consistency read (how much the wordings overlap). The thing most people have never
checked: ask the same question five times and you can get five different answers.

Run them at one temperature, or sweep a few, and look at the spread. About a minute, free, no
signup. Works with whatever model your key can reach.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/variance/variance.ipynb)
2. **Run each grey box top to bottom** with its play (>) button.
3. The page walks you through adding your API key safely, choosing a model, and typing your prompt.
   The last step runs it several times and shows the responses with a consistency read.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key**, a password-like string you get from the provider's website. The cost of each run is
yours (usually a fraction of a cent per run; this tool makes a few calls). You only need **one**
provider's key (this tool runs a single model).

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

# run the same prompt 5 times (default):
uvx llmprover-variance --model gpt-5 \
    --prompt "Name one risk of deploying this model to production."

# run it 8 times:
uvx llmprover-variance --model gpt-5 --prompt "..." --runs 8

# sweep temperatures (one run each):
uvx llmprover-variance --model gpt-5 --prompt "..." --temperatures 0,0.5,1.0
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/variance
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python variance.py --model gpt-5 --prompt "..." --runs 5
```

Key environment variables by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`. The provider is inferred from the model id.

## What it does, and what it does not

**Does (free):** runs one prompt at one model up to 10 times (optionally sweeping temperatures),
shows every response plus token cost and latency, and reports a mechanical consistency number: the
mean, min, and max wording overlap across the responses. 1.00 means identical wording, 0.00 means
no shared words.

**Does not (by design):** the consistency number is **mechanical overlap, not a quality score**. It
gives **no verdict**. It does not say which answer is better, whether any is correct, or whether the
model is stable enough for your use. You read the spread and judge for yourself.

A single judge pass can be inconsistent too (verdicts can flip on re-run). When you want consistency
that is *scored* with a reliability-checked judge, the which-layer diagnostic, and drift tracked over
time, that is [LLM Prover](https://llmprover.pysolvr.com). Background on scoring and why a single pass is
unreliable: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

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
