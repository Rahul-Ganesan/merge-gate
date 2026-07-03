"""BENCH targeting layer: git diff + changed-file -> test mapping.

The fallback-to-bounded-full-run is deliberate: never let "couldn't map a test"
silently mean "ran nothing." That failure mode is exactly what makes a verification
product untrustworthy.
"""

import subprocess
from pathlib import Path


def changed_files(base_ref: str = "origin/main") -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [f for f in out.splitlines() if f.strip()]


def unified_diff(base_ref: str = "origin/main", max_bytes: int = 60_000) -> str:
    out = subprocess.run(
        ["git", "diff", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out[:max_bytes]  # cap so the judge prompt stays bounded


def target_tests(files: list[str]) -> list[str]:
    """Heuristic mapping: src/foo/bar.py -> tests touching 'bar'. Cheap but explainable."""
    stems = {Path(f).stem for f in files}
    all_tests = [str(p) for p in Path("tests").rglob("test_*.py")] + [
        str(p) for p in Path(".").rglob("*.test.ts")
    ]
    hit = [t for t in all_tests if any(s in t for s in stems)]
    return hit or all_tests[:20]  # fall back to a bounded full run
