# Compliance Scoring

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compliance-score/compliance_score.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compliance-score/compliance_score.ipynb)

**Does your draft line up with your rules?** Paste your reference documentation (a policy, a standard,
a regulation) and your own draft (a clause, a policy, a marketing claim, a filing), and the tool reads
the draft against the reference point by point: which points are **supported**, which are **not found**
in the reference, and which **contradict** it, plus a coarse count. It is a read to help your review,
with your own key.

Unlike the verification tools here, this does not run a model to generate an answer. It checks work
you already have against documentation you supply, so it is useful even if no AI was involved in your
draft.

About a minute, free, no signup. Works with whatever model your key can reach.

> **This is a read, not a certification.** It comments on how your draft lines up with your reference;
> it will never tell you a draft is "compliant" or "approved". It is a single lightweight pass that can
> be inconsistent and can miss things, a first look to guide *your* review. It does not discharge any
> professional duty. You own your compliance; this is an instrument to assist your review. Every run
> prints this reminder.

It comes **pre-filled with a demonstration default** so your first run shows the read *running* on a
real reference and draft, the point is to watch the mechanism work, not to watch it pass.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compliance-score/compliance_score.ipynb)
2. **Run each grey box top to bottom** with its play (>) button. The first run uses the pre-filled
   demonstration so you can watch the read run.
3. The page walks you through adding your API key safely. Then paste your own reference and draft and
   re-run.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key**, a password-like string you get from the provider's website. Each run is one call, a
fraction of a cent. You only need **one** provider's key.

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

# run the demonstration default (watch the compliance read run):
uvx llmprover-compliance-score

# your own (paste inline or from files):
uvx llmprover-compliance-score --model gpt-5 \
    --reference-file policy.txt --draft-file my_clause.txt
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/compliance-score
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python compliance_score.py   # runs the demo default
```

Use `--reference`/`--reference-file` for the rules and `--draft`/`--draft-file` for your work product.
The reference and draft are text you paste (no vector store, no retrieval). Key environment variables
by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY`,
`GROQ_API_KEY`. The provider is inferred from the model id.

## What it does, and what it does not

**Does (free):** breaks your draft into its key points and, for each, reports whether your reference
supports it, is silent on it, or contradicts it, with a short note and a coarse count (e.g. "3 of 4
checked points traced to your reference") and the cost.

**Does not (by design):** it is a **single-pass qualitative read, not a compliance certification**. It
never says "compliant" or "approved". The count is a mechanical tally of one read, not a score or a
pass/fail. It can be inconsistent and can miss things, and it does not discharge any professional duty.

Compliance checking you can rely on, rubric-weighted scoring, consistency checks, a diagnostic, an
audit trail, and checking against your whole regulation or policy corpus, is
[LLM Prover](https://llmprover.pysolvr.com/?tool=compliance-score). Background on what reliable
scoring needs: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

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
basic single-pass read, not a compliance certification, and not legal, medical, tax, or other advice.
You remain responsible for your own compliance and for verifying this read as your profession or
situation requires. pysolvr is not liable for decisions made from these results.
