---
name: qa-companion
description: Build and maintain a full testing suite — the QA Companion — for any app, skill, or agent workflow, using the same file-based, idempotent, self-verifying paradigm the skills themselves follow. Four dimensions, each with its own counter: false-green tests that seed a known defect and require the check to fail (FG), idempotency tests covering every mutation the system performs (IP), full CRUD lifecycle tests for every entity (LC), and progressive-disclosure UX tests for both novice and expert paths (UX). Use whenever a user asks to "build a test suite", "test this skill/app/agent", "prove the gates actually fail", "check idempotency", "lifecycle tests", "test the novice path", "QA companion", or accepts work from an agent and wants tests instead of assurances. Runs in Codex, Claude, or any agent host with no engine, launcher, or network. Idempotent — re-running against an unchanged system reproduces the identical suite instead of writing a duplicate.
---

# QA Companion

> **Claude skill.** Install this file as `~/.claude/skills/qa-companion/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/qa-companion/SKILL.md` so the whole project shares it. Invoke it as `/qa-companion`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

Turn "it looks tested" into a suite that can prove it. The QA Companion is built on one premise borrowed from red-teaming and made mechanical: **a check that cannot be made to fail is not a check.** Every test this skill designs therefore has a defined red state, and the adversarial posture is not a vibe — it is an explicit test class with IDs. The suite is a file, its tests carry stable counters, and re-running the skill updates that file in place; it never depends on chat history surviving.

Evidence discipline matches the sibling skills: a result observed from an executed test is `measured`; a judgment rendered without execution is `agent_review`; absent evidence is `not_evaluated`, never `pass`. This skill makes no network call, reads no secret, submits no remote job, and spends nothing.

## The four test dimensions

| Dimension | Counter | What it proves | Red state |
|---|---|---|---|
| **False-green** | `FG-NNN` | Every gate, linter, validator, or review step actually fails when it should — adversarial claims become seeded-defect tests | The check stays green on a seeded defect (that is the finding) |
| **Idempotency** | `IP-NNN` | Every mutation is safe to re-run: unchanged input → identical output and an explicit no-op report; changed input → in-place update; never a duplicate artifact | A re-run rewrites bytes, bumps a version, or spawns `file (1)` |
| **Lifecycle (CRUD)** | `LC-NNN` | Every entity survives its whole life: create, read, update, delete, and the chained sequence create→read→update→re-read→delete→read-fails, plus orphan and cascade rules | An entity half-exists: readable after delete, updatable before create, or orphaned by a cascade |
| **UX paths** | `UX-NNN` | Progressive disclosure works at both ends: the novice path (defaults only, no options touched) reaches a complete, correct outcome, and the expert path can reach every advanced option without fighting the defaults | A novice hits a wall that only expert knowledge unblocks, or an expert cannot override a default |

## Workflow

Follow these steps in order. Each writes auditable content to a file.

### Step 1 — Scope

Identify the system under test: an app, a skill, an agent workflow, or a pipeline. Record its name, root path, and an input fingerprint (sha256 of the primary sources when a shell is available; byte length plus first and last 40 characters otherwise). Elicit from the user what "done" means for this suite — which dimensions are in scope (default: all four) and what may be executed versus only designed. Never modify the system under test; the suite observes and probes, it does not repair.

### Step 2 — Inventory

Build the coverage denominator before writing any test — a suite without a denominator cannot claim coverage, only anecdotes. Enumerate, each with a short stable name:

1. **Checks** — every gate, linter, validator, schema check, review step, or CI command the system claims protects it. Each becomes at least one `FG` test.
2. **Mutations** — every operation that writes, installs, generates, converts, or deletes. Each becomes at least one `IP` test. "Every mutation" is literal: a mutation without an idempotency test is listed as an uncovered item, not silently skipped.
3. **Entities** — every record, file kind, or object with a lifecycle. Each becomes at least one `LC` chain.
4. **Disclosure layers** — what a first-run user sees versus what an expert can reach (defaults, flags, config files, advanced sections). Each layer boundary becomes at least one `UX` pair.

Record what was **not** inventoried and why; scope of inventory is part of the evidence.

### Step 3 — Design false-green tests

For every check in the inventory, design a seeded-defect test: introduce a specific, minimal defect the check exists to catch (in a scratch copy, never the real tree), run the check, and require red. Name the seed precisely ("remove the final self-verify step", "corrupt one recorded hash", "plant a duplicate ID") so the test is replayable. A check that stays green on its seed is a **false-green finding** — the highest-severity result this suite produces, because it means every past green from that check is unsubstantiated. Where a check cannot be exercised (no shell, proprietary CI), design the test anyway and mark its result `not_evaluated`.

### Step 4 — Design idempotency and lifecycle tests

**Idempotency (`IP`)**: for each mutation, three probes — (a) run twice on unchanged input: outputs byte-identical and the second run explicitly reports its no-op (`unchanged`, `reused`, or equivalent); (b) change the input minimally: the same artifact updates in place, IDs stable, one delta recorded; (c) duplicate scan: no `-v2`, `(1)`, `.tmp`, or timestamp-suffixed sibling appears anywhere the mutation writes.

**Lifecycle (`LC`)**: for each entity, cover the four operations and the full chain — create it, read it back verbatim, update it and re-read the update, delete it, and require the post-delete read to fail cleanly (an error or absence, never stale content). Add the edge probes: update-before-create must fail, double-delete must be safe or explicit, and any cascade (deleting a parent) must name what happens to children — orphans are a red state unless the system documents them as intended.

### Step 5 — Design UX path tests

For each disclosure layer boundary, a **novice/expert pair**. Novice probe: starting from nothing, following only what the surface itself shows (defaults, first-run text, the README's first command), reach a complete and correct outcome — record every point where the path demands knowledge the surface never disclosed; each is a finding. Expert probe: reach every advanced option from the documented surface — record any option that is unreachable, undocumented, or silently overridden by a default. Both probes name their persona's starting knowledge explicitly so a different tester reproduces the same walk. When the host can delegate to model tiers, run the novice probe on a small model — genuine ignorance is a better novice than simulated ignorance — and the expert probe on a stronger one; either way label results by who walked the path.

### Step 6 — Emit and run the suite

Write or update the single canonical suite at `./agentic-artifacts/qa-companion.md` using the output template. The system under test gets one `QA-NNN` record; tests carry their dimension counters. Where the host has a shell and the user approves execution, run what is runnable — stdlib-only, acquiring no new dependencies — and record each result as `measured` with the observed output; everything else records `designed` with result `not_evaluated` or, for judgment-based probes such as UX walks, `agent_review`. Coverage is reported as tested-over-inventoried per dimension, with uncovered items listed by name — a percentage with no denominator shown is exactly the false-green failure this suite exists to catch.

### Step 7 — Self-verify

Before finishing, check your own work and fix what fails:

- The suite exists at its canonical path; every path and ID cited in it resolves.
- The system under test is byte-unchanged (fingerprint matches Step 1) — probes ran on scratch copies only.
- Every inventoried check has an `FG` test, every mutation an `IP` test, every entity an `LC` chain, every layer boundary a `UX` pair — or appears by name in the uncovered list.
- Every `FG` test names its seed precisely enough to replay.
- Every `measured` result is backed by observed output; nothing reads `pass` on designed-but-unrun tests.
- Every UX probe names its persona's starting knowledge.
- Counters are stable and the change log reflects reality (see idempotency contract).
- The report ends with the `## Next steps` block.

Report the result to the user as a short pass/fail list. If a check fails and cannot be fixed, say so plainly rather than shipping a suite that overstates — a QA suite that overstates is a false green about false greens.

## Output template

```markdown
# QA Companion Suite
<!-- artifact-id: qa-companion-suite | schema: v1 -->

## QA-NNN: <system under test>
- Scope: <dimensions in scope> | Execution: <approved | design-only>
- Input fingerprint: <sha256 or fingerprint>
- Inventory: checks <n> · mutations <n> · entities <n> · disclosure boundaries <n>
- Coverage: FG <tested>/<inventoried> · IP <t>/<i> · LC <t>/<i> · UX <t>/<i>
- Uncovered (by name): <items or "none">

### FG — false-green tests
| ID | Check | Seeded defect | Expected | Result | Evidence |
|---|---|---|---|---|---|
| FG-001 | <check> | <precise seed> | check goes red | red | measured |

### IP — idempotency tests
| ID | Mutation | Unchanged re-run | Changed input | Duplicate scan | Evidence |
|---|---|---|---|---|---|
| IP-001 | <mutation> | identical + reports no-op | in-place, IDs stable | clean | measured |

### LC — lifecycle tests
| ID | Entity | C | R | U | D | Chain + edges | Evidence |
|---|---|---|---|---|---|---|---|
| LC-001 | <entity> | ok | ok | ok | ok | post-delete read fails; cascades named | measured |

### UX — path tests
| ID | Boundary | Novice result | Expert result | Evidence |
|---|---|---|---|---|
| UX-001 | <layer boundary> | <complete / wall at …> | <all options reachable / blocked at …> | agent_review |

### Findings
- <false greens first, then walls, orphans, duplicate spawns — or "none">

- External effects: network=0 secrets=0 remote_jobs=0 spend_usd=0
- Unresolved: <what remains not_evaluated and why>

## Change log
- v1 (YYYY-MM-DD): initial suite

## Next steps
Optional downstream skills (this suite is complete without them):
- trust-verification-architect — place verification gates at this suite's false-green findings and uncovered items
- apply-app-harness — cite this suite's measured results as the tests-actually-run evidence in a build receipt
- agent-memory-architect — persist suite state and findings across a long-running build's cycles
```

## Idempotency contract

This skill obeys the contract it tests others against.

- **Unchanged inputs → identical output.** Re-running against a byte-identical system reproduces the same inventory, tests, counters, and text; the suite body carries no run timestamps, so nothing is rewritten and no change-log entry is added.
- **Changed inputs → in-place update.** The same system keeps its `QA-NNN` record; inventory and tests update in place, retired tests are marked `retired` rather than renumbered, and one dated change-log entry records the delta (e.g., "v2: new mutation found → IP-004 added"). Never write `qa-companion-v2.md`, `suite (1).md`, or any duplicate file.
- **New system → new record.** Append the next unused `QA-NNN`; never renumber existing records. Dimension counters (`FG/IP/LC/UX-NNN`) are stable within a record and never reused after retirement.
- Always read the existing suite first to recover IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits the system and scope directly from the user, and the suite is complete without any engine, sibling skill, or network access.

**Bridges in (optional, opt-in):** `./agentic-artifacts/trust-architecture.md` (from `trust-verification-architect`) — **Hook:** its `VG-NNN` gates are exactly the checks Step 3 turns into seeded-defect `FG` tests, so offer to import them as the check inventory instead of re-eliciting. `.app-harness/receipts/` history (from `apply-app-harness`) — **Hook:** its `tests` entries seed Step 2's check inventory, and any `not_evaluated` receipt field is a candidate uncovered item. `./agentic-artifacts/slop-pattern-review.md` (from `slop-pattern-auditor`) — offer its audited surfaces as UX probe targets for user-facing text. Use any of these only if it exists at its canonical path **and** the user confirms. If absent or declined, build the inventory from Step 2's elicitation alone; completeness is unaffected.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `trust-verification-architect` (false-green findings and uncovered items become gate locations), `apply-app-harness` (measured suite results become receipt evidence — a receipt citing this suite lists only tests this suite actually ran), and `agent-memory-architect` (suite findings persist across build cycles). Offer these; never auto-run them. The suite must be complete and useful even if every bridge is declined.

## Finish

Lead with the findings: false greens first, then coverage per dimension against its inventoried denominator, then what remains `not_evaluated`. Link the suite. State plainly which results are `measured` and which are `agent_review` or design-only — and do not claim the system is well-tested from designed-but-unrun tests alone.
