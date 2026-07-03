"""The contract: Pydantic models for the Verdict returned by evaluate_diff.

Design the response first. This structured verdict is what shows up on the PR and in
the Loom, so it must read cleanly to a human in ~5 seconds.

Decision rule (deterministic, enforced in code — not the LLM's call):
    verdict == "fail"  iff  any test failed  OR  any severity == "blocker" violation.
The judge proposes violations; the gate decides the verdict.
"""

from typing import Literal

from pydantic import BaseModel, Field


class Violation(BaseModel):
    rule: str  # rubric id, e.g. "has_tests"
    severity: Literal["blocker", "warn"]
    detail: str  # one plain-English sentence
    evidence: str = Field(  # MUST point at a real diff location
        description="file:line or failing test name taken from the diff/test output"
    )


class TestResult(BaseModel):
    ran: bool
    passed: int = 0
    failed: int = 0
    failures: list[str] = []  # normalized failing test ids
    duration_s: float = 0.0


class Verdict(BaseModel):
    verdict: Literal["pass", "fail"]
    score: float = Field(ge=0.0, le=1.0)  # 1.0 = clean
    tests: TestResult
    violations: list[Violation]
    summary: str  # <= 2 sentences the agent/human reads first
    changed_files: list[str]
