# Skills

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
prompt); the workflow itself never reads it.

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

**Claude / Claude Code** — a Claude-banner copy of every skill above is generated
automatically at `.claude/skills/<name>/SKILL.md` (or `~/.claude/skills/<name>/SKILL.md`
for personal use) and invoked with `/<name>`. Regenerate after editing a Codex source:

```bash
PYTHONPATH="$PWD" python3 scripts/generate_claude_skills.py
```

The generator rewrites only the host banner byte-for-byte from the packaged Codex
source, then self-lints the result and refuses to write a skill that fails the five
guarantees. Packaged `.skill` archives for both hosts ship in
`chatgpt-skill-packages/` and `claude-skill-packages/`.

**Any other AGENTS.md-reading agent** (Cursor, Gemini CLI, etc.) can reference a
skill's `SKILL.md` directly; see `apply-app-harness`'s own doc for the full list of
supported agent surfaces and how to install the harness across all of them at once.

## Verifying a skill

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

The consolidated, share-ready copy of all eight skills lives in
`The Auditorium/` at the project root; see `SKILL-LOCATIONS.md` for the full map.

## Lexical-precision audit (2026-07-19)

A cascade of three subagent tiers (Haiku for a mechanical hedge-word/pronoun scan,
Sonnet for cross-skill terminology consistency, Opus for definitional ambiguity in
rubrics and thresholds) read all eight skills independently and reported findings
without editing anything, so the fixes below are triaged from evidence rather than
guessed. The most serious finding: `slop-pattern-auditor`'s own worked example
contradicted its stated rubric — the rule said `legitimate` requires "a material
distinction," but every negative-parallelism pivot asserts *some* distinction, so
the rule couldn't discriminate, and the example it shipped ("not speed but
correctness") cited the exact cue word ("correct...ness") the rule listed as a
`legitimate` signal while labeling the finding `harmful`. Fixed.

**Fixed:** `slop-pattern-auditor`'s classification rubric now uses an operational
correction test ("does the sentence disprove a belief a reader plausibly held?")
instead of an unfalsifiable "material distinction" standard; its `tricolon`,
`trailing_participle`, and `bold_lead_in` catalog rows gained the same treatment
(a removability test, a defined "load-bearing," and a 3-occurrence count,
respectively); its two length thresholds (160 characters, 30 words) were
reconciled into one rule. `apply-app-harness` Step 4 referenced "its own bare
rubric above" that didn't exist in the file — a three-line rubric is now inlined.
`apply-app-harness`'s "reversible assumption" test and `agent-shape-selector`'s
Step 3 scoring (which had no tie-break rule) and Step 2 (no operational
single-vs-multi-agent test) are now concrete. `trust-verification-architect`'s
gate-altitude assignment and `model-routing-economist`'s mid-tier/commodity
boundary each gained the stated threshold they were missing.
`agent-memory-architect`'s volatility-class rule was self-contradictory (Step 1
names three lifetime classes, Step 2 stated the merge rule as a two-way split) —
now one rule. An ambiguous pronoun in `apply-app-harness`, a hedge word each in
`agent-memory-architect` and `agent-shape-selector`, an "artifact" term that meant
two different things in `apply-app-harness`/`slop-pattern-auditor` versus
everywhere else, one asymmetric `Hook` label, and two missing reciprocal
bridge-out entries were all corrected. Every `Hook` bridge now states its decline
behavior explicitly rather than leaving it to the umbrella "opt-in" to imply.
Verified with two follow-up subagent tests after the fix: Sonnet correctly applied
the new negative-parallelism test to five held-out sentences it hadn't seen
before (including one designed to require the "contrary to what you might
assume" test explicitly), and Opus confirmed `agent-shape-selector`'s new
tie-break rule resolved an unplanned tie in test data without needing to invent
its own logic.

**Deliberately not fixed:** the audit also found that five skills
(`agent-memory-architect`, `agent-shape-selector`, `model-routing-economist`,
`trust-verification-architect`, `handoff-ticket-designer`) define their
idempotency "unchanged input" boundary against the user's elicited task
description in prose, rather than a byte fingerprint the way
`slop-pattern-auditor` and `qa-companion` do. This is real but lower-severity —
these five skills' inputs are conversational by design, and fingerprinting a
normalized digest of confirmed field values is a legitimate fix but a
five-file change with limited practical payoff, so it's recorded here rather
than applied.

## Model tiers

Skill bodies name tiers (frontier / mid / commodity), never vendor models — this
matches the harness's own "bind late" principle (see `PORTABILITY-AUDIT.md`):
a machine or vendor fact may be a hint, never a frozen dependency. Bind today's
models to those tiers here, and update this table as models change without
touching any skill file.

| Tier | Current examples (July 2026) | What it's for in these skills |
|---|---|---|
| **Frontier** | Claude Opus 4.8 · GPT-5.6 Sol (OpenAI's flagship, in Codex and ChatGPT) · Grok 4.3 (xAI's flagship) | Rubric application on novel/ambiguous cases, threshold judgment calls, naming the real bottleneck or tie-break — the steps every skill's Model tier notes section flags as judgment-load-bearing |
| **Mid** | Claude Sonnet · GPT-5.6 Terra (OpenAI's cost-competitive mid tier) | Reliable once a step states its operational test explicitly, which this audit's fixes now do throughout — confirmed empirically below |
| **Commodity** | Claude Haiku · GPT-5.6 Luna (OpenAI's fastest/cheapest tier) | Mechanical, enumerable work: punctuation sweeps, templating once fields are decided, executing already-designed test probes |

Verified only for Claude's own tiers in this environment: a Sonnet subagent given
only the fixed rubric correctly classified five held-out sentences with no
contradictions, and an Opus subagent confirmed a previously-missing tie-break
rule resolved cleanly. The same reasoning — explicit, quotable operational tests
reduce judgment variance for any capable instruction-following model — extends
to GPT-5.6's and Grok's tiers by the same logic, but no test was run against
those vendors' models in this environment; treat that extension as reasoned,
not measured.

Sources for the current model lineup: [GPT-5.6: Frontier intelligence that
scales with your ambition](https://openai.com/index/gpt-5-6/) (OpenAI, confirms
the Sol/Terra/Luna three-tier split), [Grok 4.3: xAI's Cheap Frontier
Model](https://codersera.com/blog/grok-4-3-launch-guide-2026/) (confirms Grok
4.3 as xAI's current flagship).
