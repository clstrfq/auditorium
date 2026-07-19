# Skills

Seven portable Codex skills, canonical here as `skills/*/SKILL.md`. Each carries the
five design guarantees checked by `python3 scripts/lint_skills.py skills`: an ordered
five-plus-step workflow, file-based outputs at a stable canonical path, a final
self-verification step, an explicit idempotency contract (unchanged input →
identical output; changed input → in-place update; new input → new record; never a
duplicate file), and standalone operation with optional, opt-in bridges to other
skills.

Six of the seven have no reference to any harness, launcher, or `APP_HARNESS_*`
variable — they run in any agent host from the SKILL.md alone. `apply-app-harness` is
the exception: it operates the deterministic review engine in this repository when
installed, and falls back to labeled agent judgment when it is not.

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
python3 scripts/lint_skills.py skills        # all seven pass the five guarantees
sh scripts/check.sh                          # every mechanical gate this repo can run
```

## Standalone vs. harness-bridged

Every skill here is complete on its own — none requires another skill or the
harness engine to produce a useful, correct output. A few declare optional,
opt-in bridges to each other's outputs (for example, `slop-pattern-auditor` can
cross-check its `agent_review` findings against `apply-app-harness`'s deterministic
`analyze` result if that engine happens to be installed, but never requires it).
Bridges are always offered, never auto-run, and a skill's output is unaffected if
every bridge is declined.
