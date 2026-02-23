---
name: error-recovery
description: Auto-handle any command/test failure: reproduce, classify, minimal fix, rerun, report evidence.
---

# Error Recovery (Codex)

## When to activate
Activate this skill immediately when:
- Any executed command returns non-zero exit code
- Tests/lint/build fail
- App crashes, logs show exceptions, healthcheck fails

## Core loop (must follow exactly)
1) Capture Evidence
- Record: command, exit code, top 30-80 lines of stderr/stdout, and the file/line if present.
- If failure is from CI: also capture failing job step name and its log snippet.

2) Classify Failure (pick one)
- TEST_FAIL (unit/integration/e2e)
- LINT_FAIL (format/type checks)
- BUILD_FAIL (compile/bundle)
- RUNTIME_FAIL (crash at runtime)
- ENV_FAIL (missing env var/secret/config)
- DEP_FAIL (dependency resolution)
- NETWORK_FAIL (timeout, DNS, external API)
- FLAKY (non-deterministic)

3) Reproduce Locally
- Rerun the same failing command once.
- If it’s test-related, rerun with highest useful verbosity:
  - Python: `pytest -q` → then `pytest -vv`
  - Node: `npm test` → then failing test file only
- If it’s runtime: run the minimal repro path (e.g., `curl /health`, run the module entrypoint).

4) Minimal Fix Strategy
- Apply the smallest diff that plausibly fixes the root cause.
- Prefer: config/env fix → small code fix → refactor (last).
- Never “fix” by deleting tests or weakening assertions unless explicitly allowed.

5) Rerun Gate (hard requirement)
- Rerun the original failing command after changes.
- If still failing: repeat from step 1, maximum 3 iterations.
- If unresolved after 3 iterations: stop, report unknowns and the most likely root cause + next experiment.

## Reporting format (must output)
- Failed command:
- Classification:
- Root cause (1–2 sentences):
- Patch summary (files changed):
- Verification evidence (command + success output snippet):
- Remaining risks:
- Next steps if it fails again:

## Hard rules
- Do not claim success without a green rerun of the failing command.
- Do not invent environment values; if missing, mark as [[TBD]] and specify required ENV key(s).
- Keep diffs minimal.
