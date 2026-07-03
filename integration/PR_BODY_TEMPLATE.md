<!--
PR body template for a change that passed the merge-gate.
Paste the real Verdict JSON returned by evaluate_diff into the code block below.
The agent is instructed (CLAUDE.md) to attach this as evidence before opening the PR.
-->

## What & why

<one or two sentences: the task and the approach>

## Verification gate

Gated by **`merge-gate` / `evaluate_diff`** before opening this PR.
Final verdict — **`pass`** (re-run until green; blockers fixed):

```json
{
  "verdict": "pass",
  "score": 1.0,
  "tests": {
    "ran": true,
    "passed": 0,
    "failed": 0,
    "failures": [],
    "duration_s": 0.0
  },
  "violations": [],
  "summary": "Clean: targeted tests pass and no blocking rubric violations.",
  "changed_files": []
}
```

<!--
If the gate initially failed, mention the retry, e.g.:
"First run blocked on `has_tests` (blocker) — added tests/test_x.py, re-ran, now pass."
Address or justify any remaining `warn` violations here.
-->

## Notes

- Judge provider: `<anthropic/claude-sonnet-5 | gemini/gemini-2.5-flash>`
- Every violation cites a real `file:line` from the diff (ungrounded findings are dropped by the gate).
