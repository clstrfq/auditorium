# Negative Parallelism and FTPO Evaluation Harness

## Use this in any app

Run this once on your computer:

```bash
./harness install-skills
```

Run this once for each app you build:

```bash
./harness install /absolute/path/to/your-app            # Codex + Claude Code
./harness install /absolute/path/to/your-app --surface all   # every agent surface
```

Then, inside that app, check any Markdown, text, CSV, or JSONL artifact:

```bash
./tools/app-harness analyze path/to/artifact.md
```

You can also ask the agents to operate the same workflow:

- Codex: `Use $apply-app-harness for this app.`
- Claude Code: `/apply-app-harness`
- Cursor: `@apply-app-harness`
- Gemini CLI: `apply-app-harness`
- Any AGENTS.md agent: reference `.agents/skills/apply-app-harness/SKILL.md`

The command writes a review packet in `.app-harness/reviews/`. It never overwrites the
input file, submits a cluster job, reads API secrets, or spends API funds.

The generated `tools/app-harness` launcher is portable: it derives the project root from
its own location, resolves `python3` from `PATH`, and finds the engine via
`$APP_HARNESS_HOME`, then a relative hint, then an absolute hint. Move the project, move
the engine, or both — it keeps working, and when it genuinely cannot find the engine it
exits 127 naming the variable that fixes it. Check what it resolved with:

```bash
./tools/app-harness status
```

## Agent surfaces and model families

The harness integrates with two distinct kinds of LLM, kept deliberately separate.

**Agent surfaces** are the hosts that load and operate the skill. Every selected surface
receives a byte-identical copy of one canonical skill, so the workflow cannot drift
between hosts:

```bash
./harness surfaces
```

**Model families** are the lineages that *produced* the text being analyzed. The analyzer
itself never calls a model; attribution records provenance so findings can be compared
across producers:

```bash
./harness models --frozen-registry validation-proxy/gate-b/frozen-model-registry.json
```

Attribution is deliberately conservative. An identifier matching no family is
`unattributed` rather than guessed. An identifier naming two real lineages — a DeepSeek
distillation of a Qwen base names both — is `ambiguous` rather than silently assigned to
one, because collapsing it would corrupt any cross-family comparison built on top.
Attribution never asserts that a model was executed, fine-tuned, or benchmarked here.

## Skills and their design guarantees

Every skill under `skills/` carries five guarantees, enforced mechanically rather than
asserted in prose:

1. a workflow of at least five explicit, consecutively numbered steps;
2. file-based auditable outputs written to a canonical path with a stable `artifact-id`;
3. a final self-verification step;
4. an idempotency contract — unchanged inputs produce identical output, changed inputs
   update artifacts in place with stable IDs and versioned deltas, never duplicate files;
5. standalone operation with optional, opt-in bridges — each skill elicits its own inputs
   and every deliverable is complete if all bridges are declined.

Check them:

```bash
python3 scripts/lint_skills.py skills
```

The linter exits non-zero on any violation, so it can gate a build. Claude skills are
generated from the packaged Codex skills by a deterministic, idempotent converter that
rewrites only the host banner and refuses to emit a skill that fails the guarantees:

```bash
PYTHONPATH="$PWD" python3 scripts/generate_claude_skills.py
```

This repository contains a local-first, fixture-only prototype for contextual detection,
classification, rewrite verification, human review events, and traceable reporting.
It performs no network calls and creates no release receipt unless a sibling fixture event
file contains an explicit `approve_release` event with a named reviewer and reason.

The FTPO engineering build is also complete. It generates 720 deterministic examples, binds
them to a replayable reference tokenizer and candidate-score model, freezes leakage-safe
train/validation/holdout splits, runs B0-B3 across three seeds, and emits hashed delta-adapter
checkpoints plus a model-corroborated build receipt. Dataset origin and empirical claim scope
remain explicit in the machine-readable artifacts.

Run the golden flow without retaining run artifacts:

```bash
python3 scripts/run_prototype.py --fixture fixtures/corpora/golden.jsonl --dry-run
python3 -m unittest discover -s tests/e2e -v
```

Both commands run on a fresh checkout with nothing installed — the engine has no runtime
dependencies and its verification acquires none. Prove the harness survives a lift and
shift the same way:

```bash
python3 -m unittest discover -s tests/app_harness -p 'test_portability.py' -v
```

The remaining unit suites use pytest, which is declared as an optional extra rather than
assumed: `pip install -e '.[dev]'`, then `python3 -m pytest`.

Run every mechanical gate at once — skills, surface sync, evidence, portability, e2e:

```bash
sh scripts/check.sh
```

## Evidence references

An evidence catalog is what a claim gets checked against, so its references must resolve
inside this repository rather than on the machine that wrote them. In
`evals/references/ftpo-evidence-catalog-1.1.0.json` the **sha256 `content_id` is the
identifier** — machine-independent and permanent — and `path` is only a repo-relative
hint. Each source declares its `resolution`:

- `vendored` — bytes are here and hash to the recorded id; re-checkable offline.
- `external-unverifiable` — bytes are not here; the claim cannot be re-checked from a
  clone, and the catalog says so rather than pointing at a path that would not resolve.

```bash
python3 scripts/verify_evidence.py                    # report resolution state
python3 scripts/verify_evidence.py --require-offline  # fail unless everything is vendored
```

A hash mismatch is a finding, not an error to re-hash away: it means the file on disk is
no longer the artifact the claim was made against.

The shipped 1.1.0 catalog is fully vendored and `scripts/check.sh` enforces
`--require-offline`. The OpenAI release artifact is a claim-focused evidence extract,
clearly labeled as such, because the primary server rejected a direct archival download;
it is not represented as a byte-for-byte page snapshot.

Catalog `1.0.0` is **frozen, not superseded in place**: its sha256 is recorded as a build
input in `artifacts/ftpo-build-cycle-0010/build-receipt.json`, so editing it would make
that receipt's provenance claim false. It remains the correct reference for cycle-0010.

The JSON result includes the run and summary hashes, hash-ledger verification, an intentionally
blocked incompatible-comparison probe, and a nullable release receipt.

Run or replay the FTPO build:

```bash
PYTHONPATH="$PWD" python3 scripts/generate_local_s1_ftpo.py \
  fixtures/ftpo-synthetic/s0/all.jsonl fixtures/ftpo-synthetic/s1-bound
PYTHONPATH="$PWD" python3 scripts/split_ftpo_data.py \
  fixtures/ftpo-synthetic/s1-bound/all.jsonl fixtures/ftpo-synthetic/s1-bound/splits \
  --seed 20260764
PYTHONPATH="$PWD" python3 scripts/run_local_ftpo_experiment.py \
  --train fixtures/ftpo-synthetic/s1-bound/splits/train.jsonl \
  --validation fixtures/ftpo-synthetic/s1-bound/splits/validation.jsonl \
  --holdout fixtures/ftpo-synthetic/s1-bound/splits/holdout.jsonl \
  --dataset-manifest fixtures/ftpo-synthetic/s1-bound/dataset-manifest.json \
  --baseline-spec evals/baselines/ftpo-baselines-1.0.0.json \
  --evidence-catalog evals/references/ftpo-evidence-catalog-1.0.0.json \
  --output artifacts/ftpo-build-cycle-0010
```

Primary artifacts:

- `artifacts/ftpo-build-cycle-0010/build-receipt.json`
- `artifacts/ftpo-build-cycle-0010/metrics.json`
- `evals/references/ftpo-evidence-catalog-1.0.0.json`
- `scripts/slurm/ftpo_train.sbatch`
