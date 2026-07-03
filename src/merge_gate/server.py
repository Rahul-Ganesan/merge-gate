"""FastMCP server exposing the evaluate_diff tool (stdio transport)."""

from mcp.server.fastmcp import FastMCP

from .diff import changed_files, target_tests, unified_diff
from .judge import judge_diff
from .schema import Verdict
from .tests_runner import run_tests

mcp = FastMCP("merge-gate")


@mcp.tool()
def evaluate_diff(task: str, base_ref: str = "origin/main", python_repo: bool = True) -> dict:
    """Gate a proposed change BEFORE opening a PR.

    Runs targeted tests + a rubric judge over the current branch diff and returns a
    structured pass/fail verdict. Call this after implementing a task and before opening
    a PR; if verdict == 'fail', fix the listed violations and call again.
    """
    files = changed_files(base_ref)
    diff = unified_diff(base_ref)
    tests = run_tests(target_tests(files), py=python_repo)
    violations = judge_diff(task, diff)

    blocker = tests.failed > 0 or any(v.severity == "blocker" for v in violations)
    score = max(
        0.0,
        1.0
        - 0.34 * tests.failed
        - 0.25 * sum(v.severity == "blocker" for v in violations),
    )
    verdict = Verdict(
        verdict="fail" if blocker else "pass",
        score=round(score, 2),
        tests=tests,
        violations=violations,
        changed_files=files,
        summary=(
            "Blocked: "
            + "; ".join(v.rule for v in violations if v.severity == "blocker")
            + (f"; {tests.failed} test(s) failing" if tests.failed else "")
        )
        if blocker
        else "Clean: targeted tests pass and no blocking rubric violations.",
    )
    return verdict.model_dump()


def main():
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
