# llmprover-tools

Free, own-key tools for working with large language models, by [LLM Prover](https://llmprover.com).

Each tool here is **free**, runs with **your own API keys** (nothing is ever sent to a pysolvr
server), and does **one job genuinely well**. They call the provider's API directly from your
machine. The only thing that can break one is a provider changing their API.

These tools are **capability-capped, not quality-capped**: each does its job completely and well,
and stops exactly where the paid product begins. When you need more, the result of every run tells
you where to go.

## Tools

| Tool | What it does | Try it (no install) |
|------|--------------|---------------------|
| [Model Compare](tools/compare) | Ask one question of two AI models (with your own keys) and see their answers, cost, and speed side by side. | [Open in Colab ▶](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/compare/compare.ipynb) |
| [Context A/B Tester](tools/context-ab) | Ask one model one question two ways (with vs without your document, or context A vs B) and watch how the context changes the answer. | [Open in Colab ▶](https://colab.research.google.com/github/dAIvdMercer/llmprover-tools/blob/main/tools/context-ab/context_ab.ipynb) |

**New to this / not a programmer?** Click "Open in Colab" above — it runs in your browser, no
install, and walks you through each step. Open the tool's own page (the tool name link) for a plain
explanation of what you need first, including **what an API key is and where to get one**.

## You need your own API key

These tools do not include an AI model. Each uses **your own account** with a provider (OpenAI,
Anthropic, Google, etc.) via an **API key** — a password-like string you get from the provider's
website. You provide the key; the tool uses it to call the provider directly. The cost of each run is
yours (usually a fraction of a cent). Each tool's page explains where to get a key and which models it
reaches. Not sure what exists or what it costs? See
[llmprover.com/models](https://llmprover.com/models/) and
[llmprover.com/api-pricing](https://llmprover.com/api-pricing/).

## Your keys stay with you

Every tool reads your key from your environment, or from Google Colab's encrypted Secrets panel when
you run it there, and uses it to call the provider directly. **Keys are never sent to pysolvr.** You
are responsible for your own usage and costs with your providers.

**If you edit and save your own copy:** never put a key directly into a file you share or commit. The
Colab path keeps keys out of the notebook for you (it uses Colab Secrets). If a key ever does end up
somewhere public, delete it at the provider and create a new one ("rotate" it). Developers: this repo
ships a `.gitignore` excluding `.env`/secret files; a secret scan before pushing (e.g.
[gitleaks](https://github.com/gitleaks/gitleaks)) is a good habit.

## Legal

Free tools, provided as-is, no warranty. Each uses your own API key. You are responsible for your
usage and costs. Keys never leave your machine and are never sent to pysolvr. Outputs are
informational, not advice. pysolvr is not liable for decisions made from these results.
