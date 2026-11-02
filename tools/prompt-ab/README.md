# Prompt A/B Diff

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/prompt-ab/prompt_ab.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/prompt-ab/prompt_ab.ipynb)

**What does the way you phrase a prompt cost you?** Fire two (or more) prompts at one model, with
your own key, and see each response, token cost, and latency side by side. The classic lesson: a
rambling, unbounded ask uses more tokens, costs more, and runs slower than a tight, structured ask
that gets the same answer.

About a minute, free, no signup. Works with whatever model your key can reach.

It comes **pre-filled with a demonstration default** (a rambling ask next to a tight one), so your
first run already shows the point: watch the rambling prompt cost more for the same answer. The
lesson is the token and cost numbers, not a verdict the tool emits.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/prompt-ab/prompt_ab.ipynb)
2. **Run each grey box top to bottom** with its play (>) button. The first run uses the pre-filled
   rambling-vs-tight demonstration.
3. The page walks you through adding your API key safely. Then overwrite the two prompts with your
   own and re-run to compare *your* wordings.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key**, a password-like string you get from the provider's website. Each run costs a fraction
of a cent. You only need **one** provider's key (this tool runs a single model).

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

# run the demonstration default (rambling vs tight):
uvx llmprover-prompt-ab

# your own two prompts at one model (repeat --prompt for each):
uvx llmprover-prompt-ab --model gpt-5 \
    --prompt "Summarize the attached note in three bullets." \
    --prompt "TL;DR, 3 bullets:"
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/prompt-ab
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python prompt_ab.py   # runs the demo default
```

Repeat `--prompt` for each prompt (2 to 5). Add `--label` in the same order to name them. Key
environment variables by provider: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`. The provider is inferred from the model id.

## What it does, and what it does not

**Does (free):** runs 2 to 5 prompts at one model, shows each response plus token cost and latency,
and a mechanical summary (the heaviest prompt used Nx the tokens of the lightest and cost Nx as
much). Cost comes from a dated price snapshot.

**Does not (by design):** it gives **no verdict**. The token and cost numbers are mechanical counts;
the tool does not say which prompt is better, which answer is more correct, or which wording you
should use. You read the responses and the numbers and judge.

When you want prompts *scored* for quality across your real workload, the which-layer diagnostic, and
drift tracked over time, that is [LLM Prover](https://llmprover.pysolvr.com/?tool=prompt-ab).
Background on how wording drives cost: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

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
