---
name: trust-verification-architect
description: Architect verification into agent workflows that presume fallibility — citation-first outputs, pre-deployment behavioral tests, bottleneck identification, and human checkpoints at strategic (not prompt-level) altitude. Produces a file-based Trust Architecture document with enforced verification gates. Use whenever a user asks "how do I trust my agent's output", "my agent hallucinates", "verification gates", "should a human review this", "is this workflow safe to automate", wants to deploy agents on high-stakes work (claims, legal, finance, customer-facing), or is granting an agent access to files, Slack, or infrastructure and wants a pre-deployment check. Also trigger on "design for untrustworthy AI" or "citation requirements for agents". Idempotent — re-runs update the existing document in place with versioned deltas.
---

# Trust Verification Architect

> **Claude skill.** Install this file as `~/.claude/skills/trust-verification-architect/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/trust-verification-architect/SKILL.md` so the whole project shares it. Invoke it as `/trust-verification-architect`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

Organizations scale critical operations on systems that hallucinate, absorb prompt injections, and degrade contextually over time. The answer is not waiting for perfectly reliable AI — it's architecting workflows that presume fallibility and enforce verification natively. The core move is a 500-year-old auditing trick: force externalization of logic. An agent required to cite every source, step by step, before acting turns hallucinations into cheaply catchable defects (a faked quote fails its citation check and a human fixes it for dollars) instead of silent failures.

## Workflow

### Step 1 — Elicit the workflow and its stakes
Gather: the workflow being automated, each point where an agent produces output someone acts on, the blast radius of a wrong output at each point (money, legal exposure, safety, reputation), and what access the agent gets (files, comms channels, deploy rights). Rank output points by failure cost.

### Step 2 — Ask the bottleneck question
Before designing any gate, make the user name the exact organizational bottleneck this automation addresses (the "$40 question"). If they can't, record that finding prominently and warn plainly: agents pointed at an unidentified bottleneck accelerate broken processes. Don't refuse to continue — but the document must carry the warning.

### Step 3 — Design citation-first output contracts
For each high-stakes output point, define what the agent must externalize before its output counts: sources cited per claim, policy/document sections referenced, intermediate reasoning steps, and confidence rating. Specify the machine-checkable part (do all cited sources exist? do quotes match?) versus the human-judged part.

### Step 4 — Define the pre-deployment behavioral test
Before the agent gets real access, specify a 4-question behavioral test it must pass, tailored to this workflow: (1) boundary adherence — does it refuse out-of-scope actions? (2) constraint retention — does it still honor instructions late in a long context? (3) injection resistance — does adversarial content in its inputs redirect it? (4) failure honesty — does it say "I can't" rather than fabricate? Define concrete pass/fail probes for each, not vibes.

### Step 5 — Place human checkpoints at the right altitude
Position humans as mission control, not micro-managers: strategic approval gates (`VG-NNN`) at the highest-stakes transitions, sampling review for the middle, and full autonomy where failure is cheap and reversible. For each gate record: trigger, reviewer, what they check (tie it to the Step 3 citation contract), and expected review cost. A gate nobody can staff is a gate that won't happen — check staffing realism.

### Step 6 — Write the Trust Architecture artifact
Write `./agentic-artifacts/trust-architecture.md` using the output template below. Gates carry stable `VG-NNN` IDs; behavioral test probes carry `BT-NNN`.

### Step 7 — Self-verify
Check the written file and fix failures:
- File exists at the canonical path and matches the template.
- Every output point ranked in Step 1 has either a gate or an explicit "no gate — low stakes" decision; no unaccounted points.
- Every gate references a citation contract; every behavioral test probe has a concrete pass criterion.
- The bottleneck answer (or the warning about its absence) is present.
- IDs stable, change log accurate, no run timestamps in the body.
- File ends with the `## Next steps` block.
Report pass/fail to the user.

## Output template

```markdown
# Trust Architecture
<!-- artifact-id: trust-architecture | schema: v1 -->

## Workflow and stakes
<output points ranked by failure cost>

## Bottleneck finding
<the named bottleneck, or the warning that none was identified>

## Citation contracts
<per output point: what must be externalized; machine-checkable vs human-judged>

## Pre-deployment behavioral test
BT-001..BT-004: <probe> → pass criterion: <concrete>

## Verification gates
VG-NNN: <trigger> | reviewer: <who> | checks: <what> | cost: <estimate>
No-gate decisions: <point> — <why acceptable>

## Change log
- v1 (YYYY-MM-DD): initial architecture

## Next steps
Optional downstream skills (each works without them):
- handoff-ticket-designer — encode gates as ticket states with receipts
- model-routing-economist — budget the review costs and gate-triggered escalations
```

## Idempotency contract

- **Unchanged inputs → identical output.** Re-running on the same workflow yields a byte-identical file: same IDs and ordering, no new change-log entry, no run timestamps in the body.
- **Changed inputs → in-place update.** Gates keep their `VG-NNN` IDs; edits happen in place with one dated change-log entry per run describing the delta. Never write `trust-architecture-v2.md` or duplicates.
- **New gates append** with the next unused ID; removed gates are marked `status: retired`, never deleted or renumbered.
- Always read the existing artifact first to recover IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits the workflow directly, and the document is complete without any sibling artifact.

**Bridges in (optional, opt-in):** `./agentic-artifacts/shape-decision.md` (from `agent-shape-selector`) — offer to seed output points from its roles and risks; and `./agentic-artifacts/handoff-protocol.md` (from `handoff-ticket-designer`) — offer to attach gates to its ticket transitions. Use either only if it exists at its canonical path **and** the user confirms. If absent or declined, elicit everything manually; the deliverable is equally complete.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `handoff-ticket-designer` and `model-routing-economist`. Offer, never auto-run. The architecture must stand alone if every bridge is declined.
