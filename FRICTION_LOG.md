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

## Niteshift integration assumptions — verified live (happy-path task, PR #1)

- **A1 — REFUTED (headline).** A repo-root `.mcp.json` is **not** auto-loaded. Niteshift registers
  MCP servers **only via the dashboard** (Settings → Repositories → [repo] → MCP Servers → Add
  custom server → `stdio`: command/args/env). The committed `.mcp.json` is just the source of truth
  for those fields. The gate only appeared once registered in the UI.
  Ref: docs.niteshift.dev/customizing-agents/mcp
- **A2 — CONFIRMED.** `niteshift-setup.sh` runs after checkout, before the agent: the setup log
  shows `pip install` then `git fetch origin main:origin/main` succeeding, and the gate diffed
  against `origin/main`. Docs: setup script runs as root, after clone, before the agent starts.
- **A3 — CONFIRMED.** MCP server inherited the secret store: the Gemini judge ran and returned a
  grounded verdict (score 1.0, 0 violations), so `${GEMINI_API_KEY}` resolved from the **Agent-scope**
  env var into the MCP server. (Setup-scope vs. Agent-scope is a real distinction — key must be Agent.)
- **A4 — not stressed.** Eval finished in ~3s (`duration_s` 2.99); no timeout hit. Long-eval limit
  still unverified.
- **A5 — still open (strategic).** The agent *did* call the gate, but only because CLAUDE.md prompted
  it — nothing *enforced* it. It could have opened the PR without calling `evaluate_diff`. This stays
  the roadmap question for Conor: a first-class **required** verification step.

## Niteshift live-run findings (new, from the happy-path task)

- **[setup] app deps not installed by the gate snippet** — the setup script installed only
  `merge-gate`, not SENTINEL's own `requirements.txt`, so the gate's *targeted tests* had nothing to
  import until the agent hand-installed app deps. Silent false-negative risk: without that manual
  step the targeted tests would error/no-op and the gate could false-green. **Fix:** the setup script
  must install the target repo's own deps (`pip install -r requirements.txt` / `-e .`) independently
  of the gate. (Applied to `niteshift-setup.sh`.)
- **[setup] can't uninstall debian-managed `typing_extensions`** — `pip` failed to upgrade
  `typing_extensions 4.10.0` ("no RECORD file… installed by debian"). Non-fatal here, but any dep
  needing a newer version will break. Mitigate by installing into an isolated venv/uv env rather than
  the system site-packages, or `pip install --ignore-installed typing_extensions`.
- **[setup] log stream appears to hang after `git fetch`** — setup log stalled after the fetch line;
  unclear if setup or the log pipe. Watch for perceived hangs vs. real ones during the recording.
- **[interpreter] same-env requirement reconfirmed** — reproduced locally: the MCP `command: python`
  must resolve to the exact env `merge-gate` was installed into, or the server dies with
  `No module named 'merge_gate'`. Point `command` at an absolute interpreter if setup uses a venv.

- **[judge] Gemini thinking-model token starvation (real bug, now fixed)** — surfaced by Take 3 on a
  larger diff: `gemini-2.5-flash` is a *thinking* model spending ~2939 thought tokens, and those count
  against `max_output_tokens`. The judge hardcoded `max_tokens=1200`, so thinking exhausted the budget,
  the model returned **zero content parts**, and `instructor` crashed with `'NoneType' object has no
  attribute 'parts'` — **deterministically, on every retry.** Confirmed via `usage_metadata`. Fixed:
  `max_tokens` now defaults to **8192** and is overridable via `JUDGE_MAX_TOKENS`. Verified live — the
  judge returns grounded violations on a ~240-line diff with no crash. (Claude, a non-thinking judge,
  never hit this; it only bites thinking models on non-trivial diffs.)
