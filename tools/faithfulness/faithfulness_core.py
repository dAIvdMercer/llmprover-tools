"""Context-Faithfulness Check -- canonical core.

A free, own-key, capability-capped tool by pysolvr (https://pysolvr.com).

What it does
------------
You paste a SOURCE (a policy, a regulation clause, a contract section, any ground-truth text) and ask
a question. The tool (1) has the model answer your question USING that pasted source, then (2) runs a
single lightweight pass that READS the answer against the source and comments on how faithful it is:
does every claim trace back to the source, did it ADD anything the source does not say, does it
CONTRADICT the source anywhere. It is a faithfulness READ to help your own review -- a set of notes,
not a verdict.

The question all the regulated professions are really asking is "is the AI output faithful to my
source?" (tax: faithful to the code? legal: to the cited authority? medical: to the guideline?). This
gives you a quick read on exactly that, from two plain model calls with your own key.

IMPORTANT -- a read, NOT a certification
----------------------------------------
This COMMENTS on faithfulness; it never CERTIFIES compliance. It will never tell you an answer is
"compliant" or "verified". It is a single lightweight pass that can be inconsistent and can miss
things. It is a first look to guide YOUR review, not a substitute for it. If your profession requires
you to verify AI output, this does not discharge that duty. The honesty line ships in every output.

Non-negotiables (see docs/specs/FREE-TOOLS-ECOSYSTEM-SPEC.md)
-------------------------------------------------------------
- OWN-CREDS / PROVIDER-DIRECT: calls the provider's API with the user's key. NEVER a pysolvr backend.
  The "context" is text you paste, prepended to your question. No embeddings, no vector store, no retrieval.
- CAPABILITY-CAPPED: ONE lightweight judge, a basic faithfulness prompt, QUALITATIVE commentary only.
  It NEVER emits a compliance verdict. Rubric-scored faithfulness, the which-layer diagnostic
  (model ignored the context vs the context was insufficient), multi-run consistency, a compliance
  store over your whole corpus, and an audit trail are the paid product.
- INSTRUMENT, NOT ADVISOR: it helps your review; you own your compliance. (Same stance free and paid.)
- MODEL-AGNOSTIC: the user names the model their key reaches. Nothing hard-coded, never goes stale.
- PUBLISH-ONCE: thin, provider-direct -- nothing of ours for an old copy to break against.

Legal
-----
Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage and
costs. Keys never leave your machine and are never sent to pysolvr. This is a basic faithfulness read,
not a compliance certification, and not legal, medical, tax, or other advice. You remain responsible
for independently verifying AI output as your profession or situation requires. pysolvr is not liable
for decisions made from these results.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants + stable links
# ---------------------------------------------------------------------------

UPGRADE_URL = "https://llmprover.pysolvr.com"
PRICING_URL = "https://llmprover.pysolvr.com/api-pricing/"
MODELS_HELP_URL = "https://llmprover.pysolvr.com/models/"
VERIFY_HELP_URL = "https://llmprover.pysolvr.com/guides/scoring-guide/"

# The paid capabilities this free tool withholds, named plainly for the result line.
PAID_UPGRADE_CAPABILITIES = [
    "score faithfulness against a rubric",
    "tell whether the model ignored the context or the context fell short",
    "run the check several times to confirm it is consistent",
    "check faithfulness across your whole regulation or policy corpus",
    "keep an audit trail",
]

# The MANDATORY honesty line (spec: non-negotiable for the liability cohort). Ships in every output.
HONESTY_LINE = (
    "This is a basic single-pass faithfulness READ to help your review -- not a compliance "
    "certification. A single lightweight check can be inconsistent (it can change on a re-run) and can "
    "miss things. It uses no rubric, no consistency check, and no audit trail, and it does NOT "
    "discharge any professional duty to verify AI output. You own your review; this is an instrument "
    f"to assist it. For faithfulness you can rely on professionally, see {UPGRADE_URL}."
)


# ---------------------------------------------------------------------------
# Prices -- static, stamped snapshot (stale-data-is-a-backlink principle).
# ---------------------------------------------------------------------------

_PRICES_PATH = Path(__file__).with_name("prices.json")


def load_prices(path: Path = _PRICES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int, prices: dict) -> Optional[float]:
    entry = prices.get("models", {}).get(model)
    if not entry:
        return None
    return round(
        (prompt_tokens / 1000.0) * entry["input"]
        + (completion_tokens / 1000.0) * entry["output"],
        6,
    )


# ---------------------------------------------------------------------------
# Provider-direct calls -- the user's key, the provider's API, no pysolvr backend.
# Each takes (model, prompt, system, api_key) and returns (text, prompt_tokens, completion_tokens).
# ---------------------------------------------------------------------------


def _call_openai(model, prompt, system, api_key, **kw):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages)
    u = resp.usage
    return resp.choices[0].message.content, u.prompt_tokens, u.completion_tokens


def _call_anthropic(model, prompt, system, api_key, **kw):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    params = {
        "model": model,
        "max_tokens": kw.get("max_tokens", 1024),
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        params["system"] = system
    resp = client.messages.create(**params)
    text = "".join(getattr(b, "text", "") for b in resp.content)
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _call_openai_compat(model, prompt, system, api_key, base_url, **kw):
    """Grok / Together / Groq / Gemini (OpenAI-compatible) via the openai SDK + base_url."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages)
    u = resp.usage
    return resp.choices[0].message.content, u.prompt_tokens, u.completion_tokens


_PROVIDERS = [
    ("openai", lambda m: m.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")), _call_openai, "OPENAI_API_KEY", None),
    ("anthropic", lambda m: m.startswith("claude"), _call_anthropic, "ANTHROPIC_API_KEY", None),
    ("google", lambda m: m.startswith("gemini"), _call_openai_compat, "GEMINI_API_KEY",
     "https://generativelanguage.googleapis.com/v1beta/openai/"),
    ("grok", lambda m: m.startswith("grok"), _call_openai_compat, "XAI_API_KEY", "https://api.x.ai/v1"),
    ("together", lambda m: "/" in m and not m.startswith("qwen/"), _call_openai_compat, "TOGETHER_API_KEY",
     "https://api.together.xyz/v1"),
    ("groq", lambda m: m.startswith("qwen/"), _call_openai_compat, "GROQ_API_KEY", "https://api.groq.com/openai/v1"),
]


def _resolve_provider(model: str):
    for pid, matches, caller, env_var, base_url in _PROVIDERS:
        if matches(model):
            return pid, caller, env_var, base_url
    raise ValueError(
        f"Could not infer a provider for model '{model}'. Supported prefixes: gpt-/o*, claude*, "
        f"gemini*, grok*, <together org>/<model>, qwen/*. Not sure which models to use? {MODELS_HELP_URL}"
    )


def _api_key_for(model: str, env_var: str, api_keys: Optional[dict]) -> str:
    if api_keys:
        if model in api_keys:
            return api_keys[model]
        if env_var in api_keys:
            return api_keys[env_var]
    key = os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"No API key for model '{model}'. Set the {env_var} environment variable, or pass "
            f"api_keys={{'{model}': '<key>'}}. Your key stays on your machine and is never sent to pysolvr."
        )
    return key


# ---------------------------------------------------------------------------
# Round 1 -- answer the question USING the pasted source (provider-direct).
# ---------------------------------------------------------------------------

_ANSWER_SYSTEM = (
    "Answer the user's question using ONLY the SOURCE text provided. If the source does not contain "
    "the answer, say so plainly."
)


def _build_answer_prompt(source: str, question: str) -> str:
    return f"SOURCE:\n{source}\n\nQUESTION:\n{question}"


# ---------------------------------------------------------------------------
# Round 2 -- the lightweight faithfulness READ. Qualitative commentary, NOT a verdict.
# The cap: it describes faithfulness ("appears faithful / added X / contradicts Y"); it NEVER
# certifies compliance or emits a pass/fail compliance verdict.
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = (
    "You are a careful reader helping someone review an AI answer for FAITHFULNESS to a SOURCE. You "
    "are given the SOURCE text, the QUESTION, and the ANSWER. Report ONLY how well the answer sticks "
    "to the source. Do NOT judge whether the answer is correct in the world, and do NOT say it is "
    "'compliant' or 'verified' -- that is not your job. Respond with ONLY a JSON object: "
    '{\"read\": \"appears_faithful\" | \"additions\" | \"contradiction\" | \"not_in_source\", '
    '\"unsupported_claims\": [\"<claim in the answer not supported by the source>\", ...], '
    '\"contradictions\": [\"<where the answer contradicts the source>\", ...], '
    '\"note\": \"<one or two plain sentences for the reviewer>\"}. '
    'Use \"appears_faithful\" only if every claim traces to the source. Use \"additions\" if the answer '
    'adds claims the source does not support. Use \"contradiction\" if it conflicts with the source. '
    'Use \"not_in_source\" if the source does not address the question. Lists may be empty. This is a '
    "read to help a human review, not a verdict."
)

_READS = {"appears_faithful", "additions", "contradiction", "not_in_source"}
_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _build_judge_prompt(source: str, question: str, answer: str) -> str:
    return (
        f"SOURCE:\n{source}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER to read for faithfulness:\n{answer}\n\n"
        "Return the JSON read now."
    )


def _parse_judge(text: str):
    """Parse the faithfulness read. Returns a dict with read/unsupported/contradictions/note, or a
    fallback dict with the raw text if unparseable. Never raises."""
    candidate = text or ""
    m = _FENCE_RE.match(candidate)
    if m:
        candidate = m.group(1)
    try:
        obj = json.loads(candidate)
        read = str(obj.get("read", "")).strip().lower()
        if read not in _READS:
            read = None
        return {
            "read": read,
            "unsupported_claims": [str(x) for x in obj.get("unsupported_claims", []) if str(x).strip()],
            "contradictions": [str(x) for x in obj.get("contradictions", []) if str(x).strip()],
            "note": str(obj.get("note", "")).strip(),
            "raw": None,
        }
    except Exception:
        return {"read": None, "unsupported_claims": [], "contradictions": [], "note": "",
                "raw": (text or "").strip()[:400]}


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------


@dataclass
class FaithfulnessResult:
    question: str
    source: str
    model: str
    judge_model: str
    answer: Optional[str]
    read: Optional[str]
    unsupported_claims: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    note: str = ""
    judge_raw: Optional[str] = None
    answer_cost_usd: Optional[float] = None
    judge_cost_usd: Optional[float] = None
    total_cost_usd: Optional[float] = None
    prices_as_of: str = "unknown"
    attribution_line: str = ""
    honesty_line: str = HONESTY_LINE
    disclaimer: str = ""
    error: Optional[str] = None
    help_url: str = MODELS_HELP_URL
    learn_more_url: str = VERIFY_HELP_URL


DISCLAIMER = (
    "Free tool, provided as-is, no warranty. Uses your own API key. You are responsible for your usage "
    "and costs. Keys never leave your machine and are never sent to pysolvr. This is a basic "
    "faithfulness read, not a compliance certification, and not legal, medical, tax, or other advice. "
    "You remain responsible for independently verifying AI output as your profession or situation "
    "requires. pysolvr is not liable for decisions made from these results."
)


def build_attribution_line(prices_as_of: str) -> str:
    """Self-attributing result line (lives in the OUTPUT, survives someone else's UI).
    Informational, never salesy. Names the withheld paid capabilities + the staleness redirect."""
    caps = ", ".join(PAID_UPGRADE_CAPABILITIES[:-1]) + ", and " + PAID_UPGRADE_CAPABILITIES[-1]
    return (
        f"A basic single-pass faithfulness read of an AI answer against your pasted source, on your own "
        f"keys. A read to help your review, not a certification. To {caps}, see {UPGRADE_URL}. "
        f"Prices as of {prices_as_of}. Live table: {PRICING_URL}."
    )


# ---------------------------------------------------------------------------
# The core
# ---------------------------------------------------------------------------


def faithfulness_core(
    source: str,
    question: str,
    model: str,
    judge_model: Optional[str] = None,
    api_keys: Optional[dict] = None,
    prices: Optional[dict] = None,
    max_tokens: int = 1024,
) -> FaithfulnessResult:
    """Answer `question` using `source`, then run a single-pass faithfulness READ of the answer vs the
    source. Qualitative commentary, never a compliance verdict."""
    judge_model = judge_model or model
    prices = prices or load_prices()
    prices_as_of = prices.get("prices_as_of", "unknown")

    def _shell(**kw):
        base = dict(question=question, source=source, model=model, judge_model=judge_model,
                    answer=None, read=None, prices_as_of=prices_as_of,
                    attribution_line=build_attribution_line(prices_as_of), disclaimer=DISCLAIMER)
        base.update(kw)
        return FaithfulnessResult(**base)

    # Round 1: answer using the pasted source.
    try:
        _pid, caller, env_var, base_url = _resolve_provider(model)
        key = _api_key_for(model, env_var, api_keys)
        kwargs = {"max_tokens": max_tokens}
        if base_url:
            kwargs["base_url"] = base_url
        t0 = time.perf_counter()
        answer, pt, ct = caller(model, _build_answer_prompt(source, question), _ANSWER_SYSTEM, key, **kwargs)
        _ = round(time.perf_counter() - t0, 3)
        ans_cost = _cost_usd(model, pt, ct, prices)
    except Exception as exc:  # noqa: BLE001
        return _shell(error=f"model call failed: {type(exc).__name__}: {exc}")

    # Round 2: single-pass faithfulness read.
    judge = {"read": None, "unsupported_claims": [], "contradictions": [], "note": "", "raw": None}
    judge_cost = None
    judge_err = None
    try:
        jpid, jcaller, jenv, jbase = _resolve_provider(judge_model)
        jkey = _api_key_for(judge_model, jenv, api_keys)
        jkwargs = {"max_tokens": 500}
        if jbase:
            jkwargs["base_url"] = jbase
        jp = _build_judge_prompt(source, question, answer)
        jtext, jpt, jct = jcaller(judge_model, jp, _JUDGE_SYSTEM, jkey, **jkwargs)
        judge_cost = _cost_usd(judge_model, jpt, jct, prices)
        judge = _parse_judge(jtext)
        if judge["read"] is None and not judge["raw"]:
            judge_err = "the faithfulness read could not be parsed"
    except Exception as exc:  # noqa: BLE001
        judge_err = f"faithfulness read call failed: {type(exc).__name__}: {exc}"

    total = None
    costs = [c for c in (ans_cost, judge_cost) if c is not None]
    if costs:
        total = round(sum(costs), 6)

    return _shell(
        answer=answer, read=judge["read"], unsupported_claims=judge["unsupported_claims"],
        contradictions=judge["contradictions"], note=judge["note"], judge_raw=judge["raw"],
        answer_cost_usd=ans_cost, judge_cost_usd=judge_cost, total_cost_usd=total, error=judge_err,
    )


# ---------------------------------------------------------------------------
# Formatter -- the answer + the faithfulness READ (labeled findings) + the mandatory honesty line.
# Framed as notes to help a human review, never a compliance verdict.
# ---------------------------------------------------------------------------

_READ_LABEL = {
    "appears_faithful": "Appears faithful: every claim the read checked traced back to your source.",
    "additions": "Possible additions: the answer appears to include claims your source does not support.",
    "contradiction": "Possible contradiction: the answer appears to conflict with your source.",
    "not_in_source": "Your source does not appear to address this question.",
}


def format_result(result: FaithfulnessResult) -> str:
    lines: list = []
    lines.append("=" * 72)
    lines.append(f"MODEL: {result.model}   FAITHFULNESS READER: {result.judge_model}")
    lines.append(f"QUESTION: {result.question}")
    lines.append("=" * 72)

    if result.answer is None:
        lines.append(f"ERROR: {result.error}")
        lines.append("")
        lines.append(result.honesty_line)
        lines.append("")
        lines.append(result.disclaimer)
        return "\n".join(lines)

    lines.append("")
    lines.append("SOURCE (your pasted ground-truth):")
    lines.append(result.source)
    lines.append("")
    lines.append("ANSWER (model, using your source):")
    lines.append(result.answer)
    lines.append("")
    lines.append("-" * 72)
    lines.append("FAITHFULNESS READ (notes to help your review -- not a verdict):")
    if result.read is not None:
        lines.append(f"  {_READ_LABEL.get(result.read, result.read)}")
    elif result.judge_raw:
        lines.append(f"  The read did not return structured output. Raw notes: {result.judge_raw}")
    else:
        lines.append("  The faithfulness read could not be completed.")
    if result.unsupported_claims:
        lines.append("  Claims not found in your source:")
        for c in result.unsupported_claims:
            lines.append(f"    - {c}")
    if result.contradictions:
        lines.append("  Points that appear to contradict your source:")
        for c in result.contradictions:
            lines.append(f"    - {c}")
    if result.note:
        lines.append(f"  Reviewer note: {result.note}")

    costs = []
    if result.answer_cost_usd is not None:
        costs.append(f"answer ${result.answer_cost_usd:.6f}")
    if result.judge_cost_usd is not None:
        costs.append(f"read ${result.judge_cost_usd:.6f}")
    if costs:
        lines.append("Cost: " + ", ".join(costs) +
                     (f"   total ${result.total_cost_usd:.6f}" if result.total_cost_usd is not None else ""))

    lines.append("")
    lines.append("!" * 72)
    lines.append(result.honesty_line)
    lines.append("!" * 72)
    lines.append("")
    lines.append(result.attribution_line)
    lines.append(f"Not sure which models to use? {result.help_url}")
    lines.append(f"What reliable faithfulness checking needs: {result.learn_more_url}")
    lines.append("")
    lines.append(result.disclaimer)
    return "\n".join(lines)
