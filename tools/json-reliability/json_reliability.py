"""JSON / Structured-Output Reliability -- CLI.

Fire the same request at one model N times and measure how reliably it returns valid,
schema-matching JSON: a mechanical schema PASS RATE, no quality verdict. Keys are read from
environment variables (never a flag/file). Keys stay on your machine.

Run it with NO arguments and it uses a curated demonstration default: the SAME JSON request under a
LOOSE instruction vs a STRICT instruction, N runs each, side by side. You read the two pass rates and
see for yourself that the strict instruction parses more reliably. The lesson is the pass-rate
numbers, never a verdict the tool emits.

  # run the demonstration default (loose vs strict instruction):
  python json_reliability.py

  # your own: N runs of one request, checked against a schema file:
  python json_reliability.py --model gpt-5 --runs 10 \
      --prompt "Extract name and age as JSON." --schema-file person.schema.json

  # parse-only check (no schema):
  python json_reliability.py --model gpt-5 --runs 10 --prompt "Return a JSON array of 3 colors."

Set the key env var for your model's provider:
  OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, XAI_API_KEY, TOGETHER_API_KEY, GROQ_API_KEY
"""

from __future__ import annotations

import argparse
import json
import sys

from json_reliability_core import (
    RunCountError,
    format_comparison,
    format_result,
    json_reliability_core,
)

# Demonstration default (Step 1b): the SAME request for JSON, run once under a LOOSE instruction and
# once under a STRICT instruction, with a schema both are measured against. The strict instruction
# tends to produce valid matching JSON more often -- the lesson is entirely in the two pass-rate
# numbers (mechanical), it is a durable truth about prompt discipline (not a model quirk), and the
# tool emits no verdict. Lives in the CLI wrapper defaults, not in json_reliability_core.
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_RUNS = 6
DEFAULT_PROMPT = (
    "Give me a person named Ada Lovelace who was born in 1815 and works as a mathematician."
)
DEFAULT_SCHEMA = {
    "type": "object",
    "required": ["name", "birth_year", "occupation"],
    "properties": {
        "name": {"type": "string"},
        "birth_year": {"type": "integer"},
        "occupation": {"type": "string"},
    },
}
# Loose: no format discipline at all. The model often answers in prose or wraps/varies the shape.
DEFAULT_LOOSE_SYSTEM = "You are a helpful assistant."
# Strict: exact format discipline. The model is told to emit ONLY the JSON object, keys, and types.
DEFAULT_STRICT_SYSTEM = (
    "You are a strict JSON API. Respond with ONLY a single JSON object and nothing else -- no prose, "
    "no markdown, no code fences. The object must have exactly these keys: \"name\" (string), "
    "\"birth_year\" (integer), \"occupation\" (string)."
)


def _read(path, inline):
    if inline is not None:
        return inline
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


def _run_demo(model, runs) -> int:
    print("(no input given -- running the demonstration default: the same JSON request under a "
          "LOOSE instruction vs a STRICT one, {0} runs each. Read the two pass rates and see the "
          "strict instruction parse more reliably. Pass --model / --prompt to use your own.)\n"
          .format(runs))
    loose = json_reliability_core(
        prompt=DEFAULT_PROMPT, model=model, runs=runs, schema=DEFAULT_SCHEMA,
        system=DEFAULT_LOOSE_SYSTEM, label="loose instruction",
    )
    strict = json_reliability_core(
        prompt=DEFAULT_PROMPT, model=model, runs=runs, schema=DEFAULT_SCHEMA,
        system=DEFAULT_STRICT_SYSTEM, label="strict instruction",
    )
    print(format_comparison([loose, strict]))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Measure how reliably a model returns valid, schema-matching JSON (schema pass "
                    "rate, no quality verdict). With no arguments, runs a curated demonstration default."
    )
    p.add_argument("--model", default=None, help="Model id, e.g. gpt-5 (provider inferred).")
    p.add_argument("--prompt", default=None, help="The request (should ask for JSON).")
    p.add_argument("--prompt-file", help="Read the prompt from this file.")
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="How many runs (default 6, max 10).")
    p.add_argument("--schema", help="JSON Schema inline (a JSON string).")
    p.add_argument("--schema-file", help="Read a JSON Schema from this file.")
    p.add_argument("--system", help="Optional system prompt.")
    p.add_argument("--max-tokens", type=int, default=1024)
    args = p.parse_args(argv)

    # No model and no prompt -> run the loose-vs-strict demonstration default.
    if args.model is None and args.prompt is None and args.prompt_file is None:
        return _run_demo(DEFAULT_MODEL, args.runs)

    if args.model is None:
        print("error: --model is required (or pass no arguments to run the demo default)", file=sys.stderr)
        return 2

    prompt = _read(args.prompt_file, args.prompt)
    if prompt is None:
        print("error: provide --prompt or --prompt-file", file=sys.stderr)
        return 2

    schema = None
    raw_schema = _read(args.schema_file, args.schema)
    if raw_schema is not None:
        try:
            schema = json.loads(raw_schema)
        except Exception as exc:  # noqa: BLE001
            print(f"error: --schema is not valid JSON: {exc}", file=sys.stderr)
            return 2

    try:
        result = json_reliability_core(
            prompt=prompt, model=args.model, runs=args.runs, schema=schema,
            system=args.system, max_tokens=args.max_tokens,
        )
    except RunCountError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
