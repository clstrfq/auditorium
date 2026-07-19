---
name: handoff-ticket-designer
description: Design structured tickets, queues, and receipts so AI agents pass work to each other natively — eliminating the "human as the hallway" antipattern where a person copy-pastes output between agent tools. Produces a file-based handoff protocol with a machine-readable ticket schema, queue topology, and receipt rules. Use whenever a user says "my agents can't hand off work", "I'm the one moving output between tools", "design a ticket/queue system for agents", "cross-vendor agent handoffs", "how do agents pass state", or describes a workflow where Codex/Claude/local agents each do a step and a human bridges them. Also trigger when a user wants verifiable results from agents rather than chat answers. Idempotent — re-runs update the existing protocol in place with versioned deltas.
---

# Handoff Ticket Designer

> **Claude skill.** Install this file as `~/.claude/skills/handoff-ticket-designer/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/handoff-ticket-designer/SKILL.md` so the whole project shares it. Invoke it as `/handoff-ticket-designer`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

The biggest bottleneck in multi-agent systems is rarely model intelligence — it's state preservation across handoffs. When every agent loop lives in an isolated tool, the human becomes the hallway: manually copying outputs from one interface into the next prompt. This skill replaces conversational threads with structured tickets and queues. A prompt asks an agent for an *answer*; a ticket asks it for a *verifiable result* — with receipts, context metadata, and source material embedded so any agent (any vendor) can pick up the work cold.

## Workflow

### Step 1 — Map the current handoff chain
Elicit from the user: the sequence of agents/tools involved, what artifact moves between each pair, where a human currently bridges (every copy-paste is a defect to log), and which handoffs cross vendor or trust boundaries. Draw the chain as `producer → [artifact] → consumer` lines and confirm it with the user before designing anything.

### Step 2 — Define the ticket schema
Design one machine-readable ticket format (YAML or JSON) covering every handoff in the chain. A ticket must carry enough state that the receiving agent never needs a human explainer. Required fields: stable ticket ID (`HT-NNN`), objective, acceptance criteria (what makes the result *verifiable*, not just plausible), input artifacts (paths/URIs, never pasted blobs), context metadata (upstream ticket IDs, constraints, deadlines), receipt block (who did what, when, hash of outputs), and status enum (`queued | claimed | done | failed | blocked`).

### Step 3 — Design the queue topology
Decide where tickets live and how agents claim them: a directory-as-queue (`queue/pending/`, `queue/claimed/`, `queue/done/`), a tracker, or a message bus. Define claim rules (one owner per ticket), timeout/retry behavior, and dead-letter handling for failed tickets. Prefer the dumbest mechanism that survives a crash — a filesystem queue beats a clever bus you can't audit.

### Step 4 — Specify receipts and audit rules
Every state transition appends a receipt: actor, action, timestamp, output hash or pointer. Receipts make the chain auditable end-to-end and let a downstream agent verify upstream work instead of trusting it. Define who may write receipts and what a reviewer checks when a ticket is disputed.

### Step 5 — Eliminate each human hallway
For every human bridge logged in Step 1, either (a) replace it with a ticket route, or (b) deliberately keep the human — but as an *approver on a ticket* (a state transition with a receipt), not a data conduit. Record each decision; keeping a human is fine, keeping them as clipboard infrastructure is not.

### Step 6 — Write the handoff protocol artifact
Write `./agentic-artifacts/handoff-protocol.md` using the output template below, embedding the ticket schema and an example filled-in ticket. Stable IDs: routes are `RT-NNN`, tickets `HT-NNN`.

### Step 7 — Self-verify
Check the written file and fix failures before finishing:
- File exists at the canonical path and matches the template.
- Every handoff mapped in Step 1 has a route (`RT-NNN`) or an explicit "human approver" decision — no unaccounted bridges.
- The ticket schema includes ID, acceptance criteria, receipt block, and status enum.
- The example ticket validates against the schema.
- IDs stable, change log accurate, no run timestamps in the body.
- File ends with the `## Next steps` block.
Report pass/fail to the user.

## Output template

```markdown
# Agent Handoff Protocol
<!-- artifact-id: handoff-protocol | schema: v1 -->

## Handoff map
RT-NNN: <producer> → <artifact> → <consumer> | human role: none | approver

## Ticket schema
<fenced YAML/JSON schema>

## Example ticket
<fenced filled-in ticket HT-001>

## Queue topology
<mechanism, claim rules, retry/dead-letter rules>

## Receipt rules
<who writes receipts, contents, dispute review>

## Change log
- v1 (YYYY-MM-DD): initial protocol

## Next steps
Optional downstream skills (each works without them):
- trust-verification-architect — turn acceptance criteria into enforced verification gates
- agent-memory-architect — persist ticket state and receipts as durable agent memory
```

## Idempotency contract

- **Unchanged inputs → identical output.** Same handoff chain re-run produces a byte-identical file: same route/ticket IDs, same order, no new change-log entry, no embedded run timestamps.
- **Changed inputs → in-place update.** Existing routes keep their `RT-NNN` IDs; modify fields in place and append one dated change-log entry per run describing the delta. Never emit `handoff-protocol-final.md` or duplicates.
- **New routes append** with the next unused ID; removed routes are marked `status: retired`, never deleted or renumbered.
- Always read the existing artifact first to recover IDs and the current version number.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits the handoff chain directly from the user, and the protocol is complete without any sibling artifact.

**Bridges in (optional, opt-in):** `./agentic-artifacts/shape-decision.md` (from `agent-shape-selector`). If it exists at that canonical path, offer to derive the handoff map from its roles and communication pathways — use it only after the user confirms. If absent or declined, elicit the chain manually; the deliverable is identical in completeness.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `trust-verification-architect` (consumes this protocol to gate high-risk transitions) and `agent-memory-architect` (consumes it to design durable state for tickets and receipts). Offer, never auto-run. The protocol must stand on its own if every bridge is declined.
