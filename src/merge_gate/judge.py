"""SENTINEL layer: LLM-as-judge + grounding guard.

The judge can hallucinate a violation about a file that isn't in the diff;
`_enforce_grounding` deletes it. That's the difference between "AI says it's bad" and
"here's the line."
"""

import os
import re

import instructor
from pydantic import BaseModel

from .rubric import RUBRIC
from .schema import Violation

# Provider-agnostic judge. The gate's value is the grounding guard, not the model, so the
# LLM is swappable — a live proof of the model-agnostic thesis. Default stays Claude;
# set JUDGE_PROVIDER=gemini to use Gemini. instructor.from_provider reads the matching key
# from env (ANTHROPIC_API_KEY / GEMINI_API_KEY) at construction.
_PROVIDER_ALIASES = {"gemini": "google", "claude": "anthropic"}
_DEFAULT_MODEL = {"anthropic": "claude-sonnet-5", "google": "gemini-2.5-flash"}

PROVIDER = _PROVIDER_ALIASES.get(
    os.environ.get("JUDGE_PROVIDER", "anthropic").lower().strip(),
    os.environ.get("JUDGE_PROVIDER", "anthropic").lower().strip(),
)
MODEL = os.environ.get("JUDGE_MODEL", _DEFAULT_MODEL.get(PROVIDER, "claude-sonnet-5"))

# Output-token budget. Gemini 2.5 models are *thinking* models: thinking tokens count against
# max_output_tokens, so a small cap gets exhausted by thinking and the model returns zero content
# parts — instructor then crashes on `NoneType.parts`. Budget for thinking + the structured JSON,
# and let it be overridden per environment.
MAX_TOKENS = int(os.environ.get("JUDGE_MAX_TOKENS", "8192"))

# Model is bound to the client here, so create() below omits it.
client = instructor.from_provider(f"{PROVIDER}/{MODEL}")


class JudgeOut(BaseModel):
    violations: list[Violation]


JUDGE_RULES = "\n".join(
    f'- {r["id"]} ({r["severity"]}): {r["check"]}'
    for r in RUBRIC
    if r["kind"] == "judge"
)


def judge_diff(task: str, diff: str) -> list[Violation]:
    prompt = f"""You are a strict code-review gate. Task the agent was given:
<task>{task}</task>

Unified diff:
<diff>{diff}</diff>

Evaluate ONLY these rules. Emit a violation only when clearly warranted.
Every violation.evidence MUST be a file path or file:line that appears in the diff.
Rules:
{JUDGE_RULES}"""
    out = client.chat.completions.create(
        max_tokens=MAX_TOKENS,
        response_model=JudgeOut,
        messages=[{"role": "user", "content": prompt}],
    )
    return _enforce_grounding(out.violations, diff)


def _enforce_grounding(violations: list[Violation], diff: str) -> list[Violation]:
    """SENTINEL's core invariant: drop any violation whose evidence isn't in the diff."""
    files_in_diff = set(re.findall(r"^\+\+\+ b/(.+)$", diff, re.M))
    kept = []
    for v in violations:
        path = v.evidence.split(":")[0]
        if path in files_in_diff or path in diff:
            kept.append(v)
    return kept
