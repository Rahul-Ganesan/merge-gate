# Friction log

Format: `[surface] what I expected → what happened → what would've saved me N minutes`

## Build-phase findings (merge-gate itself)

- **[tests_runner] test-count parsing** — expected the plan's `re.findall("PASSED|✓")` to count
  passing tests → pytest only emits the `PASSED` token in **verbose** mode; under `-q` a pass
  is a bare `.`, so `passed` was always `0` in the Verdict → parsing the summary line
  (`N passed` / `N failed`) instead of per-test tokens works in both quiet and verbose. Fixed.

- **[tests_runner] interpreter selection** — expected `["python", "-m", "pytest"]` to run in the
  project venv → in this sandbox bare `python` resolved to a uv-managed interpreter with **no
  pytest**, so every run reported `ran=True, passed=0` (a silent false-green risk) → switched to
  `sys.executable` so tests run under the same interpreter that hosts the MCP server. Fixed.

- **[judge] import-time API key** — expected to import `server` without secrets for a smoke test →
  `judge.py` builds its Anthropic client at module import, so `import merge_gate.server` raises
  `KeyError` without `ANTHROPIC_API_KEY`, even before any tool call → consider lazy client init
  so the tool is importable/introspectable without a key. (Left as-is for SENTINEL parity; noted.)

- **[packaging] pytest not declared** — expected `pip install -e .` to make the suite runnable →
  pytest is only a runtime dep transitively (invoked via subprocess against the target repo), so
  running merge-gate's *own* tests needs a separate `pip install pytest`. Add a `[dev]` extra.

## Provider switch (Claude -> Gemini judge)

- **[judge] provider-agnostic refactor** — switched from `instructor.from_anthropic(...)` to
  `instructor.from_provider(f"{PROVIDER}/{MODEL}")`, env-driven via `JUDGE_PROVIDER`
  (`gemini` aliased to `google`). Default stays `claude-sonnet-5`. This is the model-agnostic
  thesis made literal — same rubric + grounding guard, swappable brain (plan §12 step 4).

- **[billing] Anthropic $0 balance** — a valid key still 400s with "credit balance is too low";
  moved the live judge to Gemini's free tier to unblock. Auth vs. billing are separate failures.

- **[deps] Gemini structured output needs jsonref** — `from_provider("google/...")` constructs
  fine but the first `create()` with a `response_model` raises `ConfigurationError` until
  `instructor[google-genai]` + `jsonref` are installed. Added to the `[gemini]` extra.

- **[env] .env BOM + no trailing newline** — PowerShell `Set-Content -Encoding utf8` writes a BOM
  that broke POSIX `source`, and `Add-Content` concatenated the next var onto the same line.
  Wrote `.env` as clean UTF-8 (no BOM), one `KEY=value` per line.

- **Live result:** good branch -> pass (1.0); bad branch -> fail (0.75) on a real Gemini-generated
  `has_tests` blocker, grounded at src/app/pagination.py. Grounding guard held on live output.

## Niteshift integration assumptions to verify (from plan §11) — TBD during steps 10–12

- **A1** project-scoped MCP via repo-root `.mcp.json` — unverified
- **A2** `niteshift-setup.sh` runs after checkout (working tree present) — unverified
- **A3** MCP server env inherits the task secret store — unverified
- **A4** per-tool-call timeout ≥ ~90s — unverified
- **A5** a way to make the gate *required*, not just prompted via CLAUDE.md — unverified (strategic)
