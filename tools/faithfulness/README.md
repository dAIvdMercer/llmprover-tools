# Context-Faithfulness Check

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/faithfulness/faithfulness.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/faithfulness/faithfulness.ipynb)

**Is the AI answer faithful to your source?** Paste a source, a policy, a regulation clause, a
contract section, any ground-truth, and ask a question. The tool has the model answer using that
source, then runs one lightweight pass that reads the answer back against the source and tells you:
does every claim trace to the source, did it **add** anything the source does not say, does it
**contradict** the source. It is a faithfulness **read to help your review**, with your own key.

About a minute, free, no signup. Works with whatever model your key can reach.

> **This is a read, not a certification.** It comments on faithfulness; it will never tell you an
> answer is "compliant" or "verified". It is a single lightweight pass that can be inconsistent and
> can miss things, a first look to guide *your* review, not a substitute for it. If your profession
> requires you to verify AI output, this does not discharge that duty. You own your review; this is
> an instrument to assist it. Every run prints this reminder.

It comes **pre-filled with a demonstration default** so your first run shows the read *running* on a
real source and answer, the point is to watch the mechanism work, not to watch it pass.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/faithfulness/faithfulness.ipynb)
2. **Run each grey box top to bottom** with its play (>) button. The first run uses the pre-filled
   demonstration so you can watch the read run.
3. The page walks you through adding your API key safely. Then paste your own source, type your
   question, and re-run.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key**, a password-like string you get from the provider's website. Each run makes two calls
(the answer, then the read), each a fraction of a cent. One provider's key is enough if the answering
and reading models are from the same provider.

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

# run the demonstration default (watch the faithfulness read run):
uvx llmprover-faithfulness

# your own (paste source inline or from a file):
uvx llmprover-faithfulness --model gpt-5 \
    --question "Can an employee carry unused leave into next year?" \
    --source-file leave_policy.txt
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/faithfulness
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python faithfulness.py   # runs the demo default
```

Use `--source-file` for a longer source, and `--judge-model` to use a different model for the read
than for the answer. The source is text you paste, prepended to your question (no vector store, no
retrieval). Key environment variables by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`.

## What it does, and what it does not

**Does (free):** the model answers your question using the pasted source, then one reading pass
reports a faithfulness read, appears faithful / possible additions / possible contradiction / not in
source, plus the specific claims it could not find in the source, and the cost.

**Does not (by design):** it is a **single-pass qualitative read, not a compliance certification**. It
never says "compliant" or "verified". It can be inconsistent and can miss things. It does not score
faithfulness against a rubric, tell you whether the model ignored the context or the context fell
short, or check across your whole corpus, and it does not discharge any professional duty.

Faithfulness you can rely on, rubric-scored, consistency-checked, diagnostic, auditable, and across
your whole regulation or policy corpus, is
[LLM Prover](https://llmprover.pysolvr.com/rag-evaluation/?tool=faithfulness). Background on why one
pass is not enough: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

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
basic faithfulness read, not a compliance certification, and not legal, medical, tax, or other advice.
You remain responsible for independently verifying AI output as your profession or situation requires.
pysolvr is not liable for decisions made from these results.
