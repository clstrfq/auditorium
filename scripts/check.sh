#!/bin/sh
# Every gate this repository can enforce mechanically, in one command.
#
# Runs on a fresh checkout with nothing installed: the engine has no runtime
# dependencies and neither does its verification. Use it locally or as the body
# of a CI job — there is no CI-specific step to keep in sync.
#
# Optional pytest suites are skipped with a notice rather than failing, so this
# script never reports a gate as passing when it did not run.
#
# Exit status is non-zero if any gate fails, so it can gate a build.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

python=""
for name in python3 python; do
    if command -v "$name" >/dev/null 2>&1; then python=$(command -v "$name"); break; fi
done
if [ -z "$python" ]; then
    echo "check: no python3 on PATH." >&2
    exit 127
fi

failed=0
run() {
    label=$1
    shift
    printf '\n=== %s ===\n' "$label"
    if "$@"; then
        return 0
    fi
    echo "FAILED: $label" >&2
    failed=1
}

# 1. Skills carry the five design guarantees.
run "skill guarantees" "$python" scripts/lint_skills.py skills

# 2. Every agent surface carries a byte-identical copy of the canonical skill.
run "generated claude skills are in sync" "$python" scripts/generate_claude_skills.py

# 3. Every evidence reference resolves from this repository and matches its
#    recorded content id. External-only evidence is a build failure.
run "evidence catalog" "$python" scripts/verify_evidence.py --require-offline

# 4. The harness survives a lift and shift. This is the gate that would have
#    caught the launcher freezing an interpreter path and both absolute roots.
run "portability" "$python" -m unittest discover -s tests/app_harness -p 'test_portability.py'

# 5. Evidence verifier catches seeded defects.
run "evidence verifier" "$python" -m unittest discover -s tests/app_harness -p 'test_evidence_verifier.py'

# 6. End-to-end behaviour through the public launcher.
run "end to end" "$python" -m unittest discover -s tests/e2e

# 7. Unit suites that need pytest. Reported as skipped, never as passed.
printf '\n=== unit suites (pytest) ===\n'
if "$python" -c "import pytest" >/dev/null 2>&1; then
    run "pytest units" "$python" -m pytest -q
else
    echo "SKIPPED: pytest is not installed; these suites did not run."
    echo "  install with: pip install -e '.[dev]'"
fi

printf '\n'
if [ "$failed" -eq 0 ]; then
    echo "All runnable gates passed."
else
    echo "One or more gates FAILED." >&2
fi
exit "$failed"
