"""Offline tests for the gate's deterministic logic.

The judge (LLM call) is exercised in step 9 via the MCP Inspector. These tests cover the
parts that must never regress and that need no API key: the grounding guard, output
normalization, and the Verdict contract.
"""

import os

from merge_gate.schema import TestResult, Verdict, Violation
from merge_gate.tests_runner import _normalize

# judge.py builds its Anthropic client at import time, so a key must exist to import it.
# No API call is made by _enforce_grounding — a dummy value is enough.
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-for-import")
from merge_gate.judge import _enforce_grounding  # noqa: E402


SAMPLE_DIFF = """diff --git a/src/app/pagination.py b/src/app/pagination.py
--- a/src/app/pagination.py
+++ b/src/app/pagination.py
@@ -1,3 +1,10 @@
+def paginate(items, page, size):
+    return items[page * size:(page + 1) * size]
"""


def test_grounding_keeps_violation_pointing_at_diff_file():
    v = Violation(
        rule="has_tests",
        severity="blocker",
        detail="No test added for new paginate().",
        evidence="src/app/pagination.py:1",
    )
    assert _enforce_grounding([v], SAMPLE_DIFF) == [v]


def test_grounding_drops_hallucinated_violation():
    v = Violation(
        rule="has_tests",
        severity="blocker",
        detail="Broke an unrelated module.",
        evidence="src/app/nowhere.py:99",  # not in the diff
    )
    assert _enforce_grounding([v], SAMPLE_DIFF) == []


def test_normalize_strips_ansi_timings_and_addresses():
    raw = "\x1b[31mFAILED\x1b[0m in 1.23s at 0xdeadbeef"
    assert _normalize(raw) == "FAILED in <t> at 0x<addr>"


def test_verdict_model_roundtrips():
    verdict = Verdict(
        verdict="pass",
        score=1.0,
        tests=TestResult(ran=True, passed=3),
        violations=[],
        summary="Clean.",
        changed_files=["src/app/pagination.py"],
    )
    dumped = verdict.model_dump()
    assert dumped["verdict"] == "pass"
    assert dumped["tests"]["passed"] == 3
