# merge-gate

A **merge-readiness gate** exposed as an MCP tool. Before a coding agent opens a PR,
`evaluate_diff` inspects the branch diff, runs targeted tests, applies a rubric via an
LLM-as-judge, drops any ungrounded findings, and returns a structured pass/fail `Verdict`.

The model advises; the gate enforces. Every violation points at a real line in the diff.

## Quickstart

```bash
pip install -e ".[dev]"            # Claude judge (default)
export ANTHROPIC_API_KEY=sk-...
# from inside a git repo with a feature branch:
npx @modelcontextprotocol/inspector python -m merge_gate.server
# then call evaluate_diff(task="add pagination to /runs")
```

## Judge provider (model-agnostic)

The gate's value is the grounding guard, not the model — so the judge LLM is swappable:

```bash
# Claude (default)
JUDGE_PROVIDER=anthropic  JUDGE_MODEL=claude-sonnet-5   ANTHROPIC_API_KEY=...
# Gemini
pip install -e ".[gemini]"
JUDGE_PROVIDER=gemini     JUDGE_MODEL=gemini-2.5-flash  GEMINI_API_KEY=...
```

Same rubric, same grounding guard, one env var swaps the brain.

## How it works

1. `git diff` vs base — what changed
2. map changed files → tests
3. run targeted tests (normalized output)
4. LLM-as-judge over a data-defined rubric
5. grounding guard — drop violations whose evidence isn't in the diff
6. return `Verdict{ verdict, score, tests, violations, summary, changed_files }`

**Decision rule:** `verdict == "fail"` iff any test failed **or** any `blocker` violation
exists. Deterministic — not the model's call.
