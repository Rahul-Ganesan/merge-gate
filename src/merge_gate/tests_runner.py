"""BENCH exec layer: run targeted tests + normalize output.

Strip volatile artifacts so re-runs diff cleanly and formatting != failure.
"""

import re
import subprocess
import sys
import time

from .schema import TestResult

# Strip volatile artifacts so re-runs diff cleanly (BENCH normalization).
_NOISE = [
    (re.compile(r"\x1b\[[0-9;]*m"), ""),          # ANSI colour
    (re.compile(r"\bin \d+\.\d+s\b"), "in <t>"),  # timings
    (re.compile(r"0x[0-9a-f]+"), "0x<addr>"),     # object addresses
]


def _normalize(s: str) -> str:
    for pat, rep in _NOISE:
        s = pat.sub(rep, s)
    return s


def run_tests(test_paths: list[str], py: bool = True) -> TestResult:
    if not test_paths:
        return TestResult(ran=False)
    # Use sys.executable, not bare "python": run tests under the same interpreter that
    # hosts the MCP server (the one with the project's deps), instead of whatever "python"
    # happens to be first on PATH in the sandbox.
    cmd = (
        [sys.executable, "-m", "pytest", "-q", *test_paths]
        if py
        else ["npx", "vitest", "run", *test_paths]
    )
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.time() - t0
    out = _normalize(proc.stdout + proc.stderr)

    # Parse the runner's summary counts, not per-test tokens: pytest -q and vitest both
    # report "<n> passed" / "<n> failed" in the summary line, but pytest only prints the
    # word "PASSED" in verbose mode. Reading the summary works for both, quiet or verbose.
    def _count(word: str) -> int:
        m = re.search(rf"(\d+) {word}", out)
        return int(m.group(1)) if m else 0

    failures = re.findall(r"(FAILED [^\n]+|✗ [^\n]+)", out)
    passed = _count("passed")
    failed = _count("failed") or len(failures)  # fall back to per-line count
    return TestResult(
        ran=True,
        passed=passed,
        failed=failed,
        failures=failures[:15],
        duration_s=round(dur, 2),
    )
