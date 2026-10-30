# llmprover-tools

Free, own-key tools for working with large language models, by [LLM Prover](https://llmprover.com).

Each tool here is **free**, runs with **your own API keys** (nothing is ever sent to a pysolvr
server), and does **one job genuinely well**. They call the provider's API directly from your
machine. The only thing that can break one is a provider changing their API.

These tools are **capability-capped, not quality-capped**: each does its job completely and well,
and stops exactly where the paid product begins. When you need more, the result of every run tells
you where to go.

## Tools

| Tool | What it does | Run it |
|------|--------------|--------|
| [Model Compare](tools/compare) | Fire one prompt at two models (your keys) and see responses, token cost, and latency side by side. | [Open in Colab](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compare/compare.ipynb) |

## Your keys stay on your machine

Every tool uses **your own provider API keys**, read from your environment or pasted into a notebook
cell on your own machine. **Keys are never sent to pysolvr.** You are responsible for your own usage
and costs with your providers.

### Do not commit your keys

This repo ships a `.gitignore` that excludes `.env` and common secret files. Still, a repo where you
paste keys is a repo that will eventually get a key committed by accident. Before you push anything:

- Keep keys in environment variables or an untracked `.env` (never in a tracked file or a notebook
  you commit).
- Run a secret scan on your working copy, e.g. [gitleaks](https://github.com/gitleaks/gitleaks):
  `gitleaks detect --source . --no-git` (or install a pre-commit hook).
- If you ever do commit a key, **rotate it immediately** at the provider. Rewriting git history does
  not un-leak a key that was pushed.

## Legal

Free tools, provided as-is, no warranty. Each uses your own API key. You are responsible for your
usage and costs. Keys never leave your machine and are never sent to pysolvr. Outputs are
informational, not advice. pysolvr is not liable for decisions made from these results.
