# Cost Table

[![Open In Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/cost-table/cost_table.ipynb)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/cost-table/cost_table.ipynb)

**What does your workload cost on each model?** Tell it how many input and output tokens a typical
run uses, and it shows what that run costs on every model in a dated price snapshot, cheapest first.
Add how many runs you expect per month and it projects the monthly bill too.

No API key. No signup. Nothing is sent anywhere. It is pure arithmetic over a price snapshot and the
numbers you type, so the costliest model can be many times the price of the cheapest, and this shows
you the gap in seconds.

A free tool by [pysolvr / LLM Prover](https://llmprover.pysolvr.com). It is the take-home twin of our
live pricing table at [llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

---

## Not a programmer? Start here (no installing anything)

Run it in your browser with **Google Colab** in under a minute. No install, no code, and no API key.

1. **Click this button:** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/cost-table/cost_table.ipynb)
2. **Run each grey box top to bottom** with its play (>) button.
3. The page asks for two numbers (how many tokens in, how many tokens out) and shows the cost of that
   run on every model, cheapest first.

## No API key needed

Unlike most tools here, this one does **not** call any AI model, so you do not need an account or a
key. It just multiplies the token counts you give it by each model's published price. Nothing you
type leaves your machine.

### What is a "token", and how do I know my counts?

A token is a chunk of text (roughly 3 to 4 characters, or about three-quarters of a word). Providers
bill per token, split into **input** (what you send: your prompt plus any context) and **output**
(what the model writes back). You do not need to be exact. A rough estimate of a typical run is fine:
a short question might be ~50 input tokens; a page of pasted context might be ~1,000; a paragraph
answer might be ~300 output. If you already run a workload, your provider's dashboard shows your real
per-call token usage.

Not sure what models exist or what they cost today? See
[llmprover.pysolvr.com/models](https://llmprover.pysolvr.com/models/) and
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/).

## Run it in a terminal (for developers)

No keys, no environment variables. Just the token counts.

```bash
# cost one run across every model in the snapshot:
uvx llmprover-cost-table --input-tokens 1200 --output-tokens 400

# project a monthly bill at 50,000 runs/month:
uvx llmprover-cost-table --input-tokens 1200 --output-tokens 400 --runs-per-month 50000

# only cost specific models:
uvx llmprover-cost-table --input-tokens 1200 --output-tokens 400 \
    --models gpt-4o-mini,claude-haiku-5-5,gemini-3.8-flash
```

Or clone and run:

```bash
git clone https://github.com/dAIvdMercer/llmprover-tools
cd llmprover-tools/tools/cost-table
python cost_table.py --input-tokens 1200 --output-tokens 400 --runs-per-month 50000
```

## What it does, and what it does not

**Does (free):** multiplies your input and output token counts by each model's published input and
output price, and lists the per-run cost (and projected monthly cost, if you give a volume) across
every model in the snapshot, cheapest first. Models you name that are not in the snapshot are listed
separately rather than guessed.

**Does not (by design):** it does **not recommend a model**. It ranks by cost only. The cheapest row
is the cheapest row, not advice. Choosing the cheapest model that is *still good enough for your task*
needs a quality judgment, scoring each model's answers against a bar, which is
[LLM Prover](https://llmprover.pysolvr.com/?tool=cost-table): right-sizing across your real workload,
the which-layer diagnostic, and price-and-quality drift tracked over time. Background on paying for
only the quality you need: [the scoring guide](https://llmprover.pysolvr.com/guides/scoring-guide/).

## Prices drift

`prices.json` is a dated snapshot (`prices_as_of`), not a live feed, so the numbers can lag the
providers. For the current, authoritative table see
[llmprover.pysolvr.com/api-pricing](https://llmprover.pysolvr.com/api-pricing/). You can also edit
`prices.json` locally to add a model or correct a price.

## Legal

Free tool, provided as-is, no warranty. Prices are a dated snapshot and drift; verify against the
provider and the live table before relying on them. This tool does cost arithmetic only; it does not
recommend a model. Outputs are informational, not advice. pysolvr is not liable for decisions made
from these results.
