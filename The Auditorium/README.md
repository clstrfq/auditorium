# The Auditorium

Eight skills for Codex and Claude with one shared reflex: audit, verify, gate,
receipt. Hence the name.

> **This folder is a duplicated snapshot.** It holds a byte-identical copy of every
> Codex and Claude skill from the main project — `codex-skill-packages/` (the eight
> `.skill` archives for Codex), `claude-skill-packages/` (the same eight for Claude),
> and `skills/` (the canonical, unpacked `SKILL.md` source directories). The live,
> lintable source of truth stays in the main project's `skills/`,
> `chatgpt-skill-packages/`, and `claude-skill-packages/`; regenerate and verify there
> (`scripts/lint_skills.py`, `scripts/generate_claude_skills.py`, `scripts/check.sh`),
> then re-copy into this folder — it has no scripts of its own.

Eight portable Codex skills, canonical here as `skills/*/SKILL.md`. Each carries the
five design guarantees checked by `python3 scripts/lint_skills.py skills`: an ordered
five-plus-step workflow, file-based outputs at a stable canonical path, a final
self-verification step, an explicit idempotency contract (unchanged input →
identical output; changed input → in-place update; new input → new record; never a
duplicate file), and standalone operation with optional, opt-in bridges to other
skills.

All eight require nothing beyond their own `SKILL.md` to produce a complete,
correct output: none reads another `.md` file as part of its required workflow. Seven
have no dependence on any harness, launcher, or `APP_HARNESS_*` variable — they
run in any agent host from the file alone (`qa-companion` names the harness's
receipt folder only inside an optional bridge-in it works fully without). `apply-app-harness` is the one skill that
*can* operate a deterministic review engine in this repository when it is installed
(`./tools/app-harness`), but its evidence vocabulary, receipt schema, and contract
rules are written directly into its own `SKILL.md`, not read from a sibling
`references/` file — when the engine is absent it falls back to labeled agent
judgment (`agent_review`) using that same self-contained text. `apply-app-harness`'s
`agents/openai.yaml` is optional Codex UI metadata (a display name and default
prompt); the workflow itself never reads it. `apply-app-harness` is also the one
skill packaged identically for both hosts here — it is explicitly designed to install
byte-identically across every agent surface, so its `codex-skill-packages/` and
`claude-skill-packages/` archives are the same bytes on purpose, not an oversight.

## Skill index

| Skill | What it produces | Reach for it when |
|---|---|---|
| **apply-app-harness** | An App Harness Report + build receipt (contract → inspect → change → verify → attribute → receipt → self-verify) | Building, changing, or releasing an app and you want a replayable, receipted build with AI-output review and model attribution |
| **slop-pattern-auditor** | A Slop Pattern Review flagging negative parallelism, tricolons, em/en dashes, colon lead-ins, semicolon splices, trailing participles, curly quotes, transition pileups, and bold lead-ins, each labeled harmful/legitimate/uncertain with fact-preserving rewrites | Checking any text or model output for AI "tells" — no engine or launcher required, works standalone in any host |
| **agent-shape-selector** | A Shape Decision Record picking a multi-agent topology (single agent, Orchestrator-Worker, Pipeline, Debate/Review, Coordinated Stackelberg, or none) | Deciding how to structure a multi-agent workflow before building it |
| **agent-memory-architect** | A Memory Architecture spec: markdown-based stores, write/read/compaction rules, continuity guarantees | An agent needs to hold state across sessions or multi-day tasks and currently forgets everything |
| **handoff-ticket-designer** | A handoff protocol: ticket schema, queue topology, receipt rules | Multiple agents (or agent + human) pass work between each other and a person is manually bridging the gap |
| **model-routing-economist** | A routing policy and cost model (frontier planner, commodity executors) | Inference spend is too high and tasks could route to cheaper models without losing quality |
| **trust-verification-architect** | A Trust Architecture document with enforced verification gates | Deploying agents on work where a wrong or hallucinated output is costly, and you need human checkpoints placed at the right altitude |
| **qa-companion** | A QA Companion Suite with four counted test dimensions: false-green tests that seed defects and require checks to fail (FG), idempotency tests for every mutation (IP), full CRUD lifecycle chains for every entity (LC), and novice/expert progressive-disclosure UX probes (UX) — coverage always reported against a named denominator | Accepting work from an agent or shipping a system whose gates have only ever been seen green, and you want tests that can prove the checks actually fail when they should |

## Using a skill

**Codex** — install to `~/.codex/skills/<name>/SKILL.md` for personal use, or keep it
in-repo and reference it from `AGENTS.md`. Invoke with `$<name>` (e.g. `$slop-pattern-auditor`).
The `codex-skill-packages/*.skill` archives in this folder unzip to that layout.

**Claude / Claude Code** — install to `.claude/skills/<name>/SKILL.md` (or
`~/.claude/skills/<name>/SKILL.md` for personal use) and invoke with `/<name>`. The
`claude-skill-packages/*.skill` archives in this folder unzip to that layout. In the
main project, the Claude copies are generated automatically from the Codex sources:

```bash
PYTHONPATH="$PWD" python3 scripts/generate_claude_skills.py
```

The generator rewrites only the host banner byte-for-byte from the packaged Codex
source, then self-lints the result and refuses to write a skill that fails the five
guarantees.

**Any other AGENTS.md-reading agent** (Cursor, Gemini CLI, etc.) can reference a
skill's `SKILL.md` directly; see `apply-app-harness`'s own doc for the full list of
supported agent surfaces and how to install the harness across all of them at once.

## Verifying a skill

Run these from the main project root (this folder has no `scripts/` of its own):

```bash
python3 scripts/lint_skills.py skills        # all eight pass the five guarantees
sh scripts/check.sh                          # every mechanical gate this repo can run
```

## Standalone vs. harness-bridged

Every skill here is complete on its own — none requires another skill or the
harness engine to produce a useful, correct output. Several declare optional,
opt-in bridges to each other's outputs (for example, `slop-pattern-auditor` can
cross-check its `agent_review` findings against `apply-app-harness`'s deterministic
`analyze` result if that engine happens to be installed, but never requires it).
Bridges are always offered, never auto-run, and a skill's output is unaffected if
every bridge is declined.

## Hooks — combining skills for a more powerful outcome

Every skill still runs alone. These hooks are the specific, named points where
running two skills together produces something neither produces by itself. Each
is opt-in and each skill declares in its own `## Standalone operation and
bridges` section what it does when the hook is not taken.

| Hook | What it unlocks |
|---|---|
| `apply-app-harness` Step 4 → `slop-pattern-auditor` | When the deterministic launcher is unavailable, apply-app-harness's manual-review fallback stops being an ad hoc "mimic the review" and becomes a named, consistent procedure — every app that hits this fallback gets the same rubric, not a fresh improvisation each time. |
| `slop-pattern-auditor` → `trust-verification-architect` | A Slop Pattern Review's harmful/uncertain counts, grouped by output surface, become candidate verification-gate locations instead of a report nobody acts on — the surfaces with recurring formulaic patterns are exactly where a gate belongs. |
| `slop-pattern-auditor` → `model-routing-economist` | Per-model-family harmful-finding rates become one input to tier reassignment — evidence, not proof by itself, that a family is a weaker fit for rote generation. |
| `apply-app-harness` → `agent-memory-architect` | A multi-cycle build's receipt history and unresolved items seed a durable `state.md`/`decisions.md` store, so a long-running build stops re-deriving its own history at the start of every session. |
| `agent-shape-selector` → `model-routing-economist` / `handoff-ticket-designer` / `trust-verification-architect` | A Shape Decision Record's roles, tiers, and communication pathways seed the workload inventory, ticket routes, and gate placement of the three downstream skills, instead of each one re-eliciting the same architecture from scratch. |
| `handoff-ticket-designer` ↔ `agent-memory-architect` / `trust-verification-architect` | A handoff protocol's ticket schema seeds memory stores for ticket state and receipts, and its transitions become the attachment points for verification gates. |
| `trust-verification-architect` ↔ `qa-companion` | Every `VG-NNN` gate the architecture declares becomes a seeded-defect false-green test proving the gate actually fails when it should; in return, the suite's false-green findings and uncovered items are exactly where the next gates belong. |
| `apply-app-harness` ↔ `qa-companion` | The build receipt's tests list and `not_evaluated` fields seed the suite's check inventory; the suite's `measured` results become the receipt's tests-actually-run evidence — a receipt backed by a suite that has proven its own checks can fail. |
| `slop-pattern-auditor` → `qa-companion` | Audited text surfaces become UX probe targets, so the novice/expert walks cover the same user-facing copy the pattern audit flagged. |

None of these hooks changes what a skill needs to run — they only describe what
becomes possible, faster, when the upstream artifact already exists at its
canonical path and the user confirms using it.

## Naming policy

Reviewed 2026-07-19; three deliberate decisions:

1. **Nothing code-wired gets renamed.** `apply-app-harness` is the weakest name
   for a human reader, but it is wired into the harness engine (installer,
   launcher, installed surface directories, existing receipts), so it keeps its
   name and this README carries the human explanation instead.
2. **`slop-pattern-auditor` keeps its name for an AI-literate audience.** If you
   share these skills with non-technical readers, rename it `ai-tell-auditor` at
   share time — the skill body needs no other change.
3. **Frontmatter descriptions are written for agents, on purpose.** They are
   long and trigger-phrase-dense so hosts invoke the right skill at the right
   moment. Humans should read the Skill index table above instead — that is the
   human surface, and the two are maintained to say the same thing in different
   registers.
