# JSON / Structured-Output Reliability

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/json-reliability/json_reliability.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/json-reliability/json_reliability.ipynb)

**How reliably does this model return the JSON your code depends on?** Fire the same request at one
model several times (your own key) and measure the **schema pass rate**: per run, did it parse as
JSON and match your schema, and across all runs, how often. The thing that burns agent and tool
builders: a model that returns good JSON *most* of the time still breaks the pipeline on the one run
that does not.

About a minute, free, no signup. Works with whatever model your key can reach.

It comes **pre-filled with a demonstration default** (the same request under a *loose* instruction
vs a *strict* one), so your first run already shows the point: the strict instruction parses more
reliably. The lesson is the two pass-rate numbers, not a verdict the tool emits.

A free, own-key tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in about a minute. No install, no code.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/json-reliability/json_reliability.ipynb)
2. **Run each grey box top to bottom** with its play (>) button. The first run uses the pre-filled
   loose-vs-strict demonstration.
3. The page walks you through adding your API key safely. Then overwrite the prompt and schema with
   your own and re-run to measure *your* request.

## What you need: an API key (and what that is)

This tool does not include an AI model. It uses **your own account** with an AI provider via an
**API key**, a password-like string you get from the provider's website. Each run costs a fraction
of a cent, and this tool makes several calls. You only need **one** provider's key (it runs a single
model).

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

# run the demonstration default (loose vs strict instruction, side by side):
uvx llmprover-json-reliability

# your own: N runs of one request, checked against a schema file:
uvx llmprover-json-reliability --model gpt-5 --runs 10 \
    --prompt "Extract the person's name and age as JSON." \
    --schema-file person.schema.json

# parse-only check (no schema): passes if the response is any valid JSON:
uvx llmprover-json-reliability --model gpt-5 --runs 10 \
    --prompt "Return a JSON array of three colors."
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/json-reliability
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python json_reliability.py   # runs the demo default
```

`--schema` / `--schema-file` take a JSON Schema. With a schema, a run passes only if the response
parses **and** validates against it; without one, a run passes if it is any valid JSON. A ```` ```json ````
code fence around the output is stripped before parsing (many models add one even when asked not to),
so fencing alone is not counted as a failure. Key environment variables by provider: `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `TOGETHER_API_KEY`, `GROQ_API_KEY`. The provider
is inferred from the model id.

## What it does, and what it does not

**Does (free):** runs one request at one model up to 10 times, reports per run whether the output
parsed as JSON and matched your schema, and the aggregate **schema pass rate** (e.g. "7 of 10 runs
produced valid matching JSON"). Cost and latency per run come from a dated price snapshot.

**Does not (by design):** the pass rate is a **mechanical count, not a quality score**. It gives
**no verdict**. It does not say the JSON content is *correct*, that your schema is well-designed, or
that one model is better than another. It counts parses and schema matches; you read the rate and
judge.

When you want structured-output reliability *scored* across your real workload, a canary that catches
a silent model swap, the which-layer diagnostic, and drift tracked over time, that is
[LLM Prover](https://llmprover.pysolvr.com/?tool=json-reliability). Background on why one pass is not
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
costs. Keys never leave your machine (or your Colab account) and are never sent to pysolvr. Outputs
are informational, not advice. pysolvr is not liable for decisions made from these results.
