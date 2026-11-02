# Model Compare -- pre-configured pair notebooks

These are thin, pre-configured editions of the [Model Compare](../) tool, one per popular model
pairing. Each notebook runs the **same** `compare_core` as the main tool; it just comes pre-filled
with two models and an everyday (or coding) prompt so you can run a head-to-head in one click.

| Notebook | Pre-filled pair (as of 2026-11-02) |
|----------|------------------------------------|
| `compare-claude-vs-chatgpt.ipynb` | Claude (`claude-opus-5-5`) vs ChatGPT (`gpt-5`) |
| `compare-chatgpt-vs-gemini.ipynb` | ChatGPT (`gpt-5`) vs Gemini (`gemini-4-argon`) |
| `compare-grok-vs-chatgpt.ipynb` | Grok (`grok-4.7`) vs ChatGPT (`gpt-5`) |
| `compare-claude-vs-gemini.ipynb` | Claude (`claude-opus-5-5`) vs Gemini (`gemini-4-argon`) |
| `compare-grok-vs-claude.ipynb` | Grok (`grok-4.7`) vs Claude (`claude-opus-5-5`) |
| `compare-grok-vs-gemini.ipynb` | Grok (`grok-4.7`) vs Gemini (`gemini-4-argon`) |

**The pre-filled pair is a convenient starting point, not a fixed configuration.** Models change
constantly; every notebook tells you to edit the two IDs to compare any models your key can reach, and
points at the [API Pricing page](https://llmprover.pysolvr.com/api-pricing/) (current models + prices,
with copy-paste code) and the [Models page](https://llmprover.pysolvr.com/models/). The demonstration
(two models head-to-head on a task) is the durable lesson; the specific models are the editable
example.

Own-creds, provider-direct, no verdict, same cap as the main tool. Keys never leave your machine. See
the [Model Compare README](../README.md) for the full what-it-does / what-it-does-not and key safety.
