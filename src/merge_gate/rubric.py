"""The rubric as data — auditable rules, easy to talk about in the interview.

Each rule has a `kind`:
  - "deterministic": decided by code (e.g. did the targeted tests pass).
  - "judge": evaluated by the LLM-as-judge, then grounded against the diff.
"""

RUBRIC = [
    {
        "id": "tests_pass",
        "severity": "blocker",
        "check": "All targeted tests pass.",
        "kind": "deterministic",
    },
    {
        "id": "has_tests",
        "severity": "blocker",
        "check": "Any change to source under src/ or app/ has a corresponding test change.",
        "kind": "judge",
    },
    {
        "id": "no_forbidden_files",
        "severity": "blocker",
        "check": "Diff does not modify .env, secrets, CI credentials, or lockfiles unless the task explicitly asked.",
        "kind": "judge",
    },
    {
        "id": "grounded_in_task",
        "severity": "warn",
        "check": "Every changed file is plausibly required by the task description; flag scope creep.",
        "kind": "judge",
    },
    {
        "id": "no_silent_api_change",
        "severity": "warn",
        "check": "Public function signatures / exported API changes are covered by a test or noted in the PR body.",
        "kind": "judge",
    },
]
