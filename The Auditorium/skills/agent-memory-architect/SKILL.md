---
name: agent-memory-architect
description: Design persistent, markdown-based memory for AI agents so they hold state across sessions, days, and multi-stage tasks — memory stores, write/read/compaction rules, and continuity guarantees that outlast any single context window. Produces a file-based Memory Architecture spec. Use whenever a user says "my agent forgets everything between runs", "design agent memory", "persistent state for my agent", "markdown memory architecture", "context continuity", "my codebase is older than the team's memory of it", or is setting up an agent for multi-day/long-horizon work. Also trigger when a user wants an agent to act as a structural partner that monitors system integrity over time rather than an ephemeral generator. Idempotent — re-runs update the existing spec in place with versioned deltas.
---

# Agent Memory Architect

> **Claude skill.** Install this file as `~/.claude/skills/agent-memory-architect/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/agent-memory-architect/SKILL.md` so the whole project shares it. Invoke it as `/agent-memory-architect`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

Human working memory is the original architectural bottleneck: as codebases age past ~18 months, humans lose context and entropy wins. Agents have the opposite problem — they can hold enormous context in active attention, but lose *everything* between sessions unless memory is designed deliberately. This skill designs that memory: durable, plain-text (markdown) stores that an agent reads on wake, writes on meaningful events, and compacts on schedule — turning an ephemeral generator into a structural partner with continuity. Most of a useful memory corpus accretes from structured dialogue with the agent itself; the architecture's job is to give that accretion shape.

## Workflow

### Step 1 — Elicit the continuity requirements
Gather: what the agent must remember across sessions (decisions, project state, preferences, open threads, environment facts), how long each class of fact stays true (forever / weeks / per-task), who else reads or writes the memory (other agents? humans?), and any privacy constraints on what may be persisted.

### Step 2 — Partition memory into stores
Design named stores (`MEM-NNN`), each a markdown file with a single purpose — e.g. `identity.md` (stable facts and preferences), `decisions.md` (append-only decision log with rationale), `state.md` (current task state, rewritten freely), `threads.md` (open loops awaiting events). One store per lifetime class from Step 1 (forever / weeks / per-task — three stores minimum); never place a shorter-lived class in a longer-lived store, or compaction will destroy facts that were meant to persist. A class may split across multiple stores by purpose (e.g. `identity.md` and `decisions.md` both hold "forever" facts, split by kind), but two classes must never merge into one store.

### Step 3 — Define write and read discipline
For each store: when the agent writes (on decision, on task completion, on user correction — not on every message), the entry format (dated, one fact per line, source noted), and the read order on session start (default identity → state → threads, with decisions on demand — record whichever order this spec actually uses if it differs). Cap what gets loaded by default — memory that always fully loads is just a slower context window.

### Step 4 — Define compaction and conflict rules
Specify per store: maximum size before compaction, how to compact (summarize aged entries, drop superseded state, never silently drop decisions — mark them superseded), and conflict resolution when a new fact contradicts a stored one (newest wins for state; contradictions in identity get flagged to the user, not auto-resolved).

### Step 5 — Plan multi-agent access (if applicable)
If multiple agents share memory: which stores are shared vs. private, write-locking or single-writer rules, and how a receiving agent verifies it has the latest state. If single-agent, record that explicitly so the spec is unambiguous.

### Step 6 — Write the Memory Architecture artifact
Write `./agentic-artifacts/memory-architecture.md` using the output template below, including a bootstrap section: the initial contents of each store so the user can start immediately.

### Step 7 — Self-verify
Check the written file and fix failures:
- File exists at the canonical path and matches the template.
- Every continuity requirement from Step 1 maps to exactly one store; every store has write triggers, read order, and compaction rules.
- No store mixes volatility classes; decision logs are append-only with a supersede rule.
- Privacy constraints from Step 1 are reflected in what stores are allowed to contain.
- IDs stable, change log accurate, no run timestamps in the body.
- File ends with the `## Next steps` block.
Report pass/fail to the user.

## Output template

```markdown
# Agent Memory Architecture
<!-- artifact-id: memory-architecture | schema: v1 -->

## Continuity requirements
<what must persist, lifetime class, readers/writers, privacy limits>

## Stores
MEM-NNN: <filename> | purpose | volatility class | write triggers | read order | size cap | compaction rule

## Conflict rules
<per class: newest-wins / flag-to-user / append-and-supersede>

## Multi-agent access
<shared vs private, locking, freshness check — or "single-agent" explicitly>

## Bootstrap contents
<initial markdown for each store, fenced>

## Change log
- v1 (YYYY-MM-DD): initial architecture

## Next steps
Optional downstream skills (each works without them):
- handoff-ticket-designer — persist ticket state and receipts into these stores
- trust-verification-architect — audit what the agent is allowed to remember and cite
```

## Model tier notes

Frontier or mid-tier judgment is worth spending on Step 2 (partitioning stores by lifetime class) and Step 4 (conflict-rule design) — the store boundaries and supersede rules a bad call here compounds every session after. Commodity tier is safe, unsupervised, for Step 6's bootstrap-content generation and templating once the stores are already defined. Which concrete model sits in which tier changes over time and by vendor; bind that mapping in the project README, not in this file.

## Idempotency contract

- **Unchanged inputs → identical output.** Re-running on the same requirements yields a byte-identical file: same store IDs and ordering, no new change-log entry, no run timestamps in the body.
- **Changed inputs → in-place update.** Stores keep their `MEM-NNN` IDs; edits happen in place with one dated change-log entry per run describing the delta. Never write `memory-architecture-new.md` or duplicates.
- **New stores append** with the next unused ID; removed stores are marked `status: retired`, never deleted or renumbered.
- Always read the existing artifact first to recover IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits requirements directly, and the spec (with bootstrap contents) is complete without any sibling artifact.

**Bridges in (optional, opt-in):** `./agentic-artifacts/handoff-protocol.md` (from `handoff-ticket-designer`). If present at that canonical path, offer to add stores for ticket state and receipts derived from its schema — use it only if it exists at that canonical path **and** the user confirms. If absent or declined, design from elicited requirements alone; completeness is unaffected. Prior App Harness Reports and receipts (from `apply-app-harness`, canonically under `.app-harness/receipts/`) — **Hook:** if present, offer a `decisions.md`/`state.md` store seeded from that history's unresolved items and change log, so a multi-cycle build persists what has already been tried instead of re-deriving it each session. If declined or absent, design from elicited requirements alone; completeness is unaffected either way.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `handoff-ticket-designer` and `trust-verification-architect`. Offer, never auto-run. The spec must be fully usable if every bridge is declined.
