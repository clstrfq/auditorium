---
name: model-routing-economist
description: Build a model-routing policy and cost model that keeps frontier models for planning and routes rote execution to commodity models — the "premium planner, cheap executors" pattern that achieves ~90%+ of all-frontier performance at roughly half the cost. Produces a file-based routing policy with decision rules, per-scenario cost projections, and runaway-cost guardrails. Use whenever a user says "we're spending too much on the big model", "which model should handle which task", "cost out my agent workflow", "is it worth routing to a cheaper model", "my agent burned a million tokens on a digest", or wants a budget before approving an agentic project. Also trigger on any request to compare all-frontier vs hybrid-routed deployment costs. Idempotent — re-runs update the same policy in place with versioned deltas.
---

# Model Routing Economist

> **Claude skill.** Install this file as `~/.claude/skills/model-routing-economist/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/model-routing-economist/SKILL.md` so the whole project shares it. Invoke it as `/model-routing-economist`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

Pointing a frontier model at trivial tasks is the fastest way to make an agent system economically absurd; so is letting an unrouted local agent loop until it burns 1.6M tokens generating a daily digest. Competitive advantage isn't access to cheap models — it's the capacity to orchestrate them. The benchmark pattern to internalize: a frontier planner directing cheaper executors reached 86.8% vs 90.8% all-frontier accuracy on BrowseComp while cutting cost per problem from $40.56 to $18.53, and ~92% of SWE-bench Pro performance at ~63% of cost. This skill turns that pattern into an explicit, auditable routing policy.

## Workflow

### Step 1 — Inventory the workload
Elicit from the user: the task types flowing through the system (planning, coding, extraction, summarization, review…), rough monthly volume per type, token profile per task (input-heavy? output-heavy?), and quality floor per type (where is "almost as good" acceptable, and where is it not). If a shape or role breakdown already exists, map task types to roles.

### Step 2 — Classify tasks by required cognition
Sort each task type into tiers: **frontier-required** (architectural planning, goal harnessing, ambiguous judgment), **mid-tier** (routine coding, structured analysis), **commodity** (extraction, formatting, rote transforms), **no-LLM** (deterministic — write a script instead). Be aggressive about pushing work down-tier; the planner/advisor role is usually the only place frontier pricing earns its keep.

### Step 3 — Assign models and write routing rules
For each tier pick a concrete model and price point (ask the user which providers are available; use their current per-token prices — verify prices rather than assuming). Write explicit routing rules (`RR-NNN`): trigger condition → model → escalation path (when a cheap model's output fails review, who escalates to what). Include a fallback rule for refusals or outages.

### Step 4 — Model the economics
Compute at least three scenarios with the arithmetic shown: (a) **all-frontier baseline**, (b) **routed** per the rules, (c) **routed + caching/batching** where applicable. Show monthly cost per scenario, cost per task, and the quality trade you're accepting (with the benchmark analogies above as reference points, clearly labeled as analogies). State every assumption in an assumptions table so the math is auditable.

### Step 5 — Add runaway-cost guardrails
Define per-agent token budgets, loop caps, cache requirements, and a kill threshold (spend rate that halts the system). Unbounded agents without structural limits are how $8 builds become $800k year-one bills.

### Step 6 — Write the routing policy artifact
Write `./agentic-artifacts/routing-policy.md` using the output template below. Rules carry stable `RR-NNN` IDs; scenarios carry `SC-NNN`.

### Step 7 — Self-verify
Check the written file and fix failures:
- File exists at the canonical path and matches the template.
- Every task type from Step 1 is covered by exactly one routing rule; every rule has an escalation path.
- Scenario math recomputes correctly (redo the arithmetic; don't eyeball it) and every figure traces to a stated assumption.
- Guardrails include a numeric kill threshold.
- IDs stable, change log accurate, no run timestamps in the body.
- File ends with the `## Next steps` block.
Report pass/fail to the user.

## Output template

```markdown
# Model Routing Policy
<!-- artifact-id: routing-policy | schema: v1 -->

## Workload inventory
<task type | volume | token profile | quality floor>

## Routing rules
RR-NNN: <condition> → <model @ $/Mtok in, $/Mtok out> → escalation: <path>

## Cost scenarios
SC-001 all-frontier: <math>
SC-002 routed: <math>
SC-003 routed+cached: <math>
### Assumptions
<numbered, each referenced by the math above>

## Guardrails
<per-agent budgets, loop caps, kill threshold>

## Change log
- v1 (YYYY-MM-DD): initial policy

## Next steps
Optional downstream skills (each works without them):
- handoff-ticket-designer — encode escalation paths as ticket routes between model tiers
- trust-verification-architect — place review gates where cheap-model output needs checking
```

## Idempotency contract

- **Unchanged inputs → identical output.** Same workload re-run yields a byte-identical file: same IDs and ordering, no new change-log entry, no run timestamps in the body.
- **Changed inputs → in-place update.** Rules keep their `RR-NNN` IDs; prices and volumes update in place with one dated change-log entry per run describing the delta (e.g., "v3: executor price drop → SC-002 recomputed"). Never create `routing-policy-updated.md` or any duplicate.
- **New task types append** new rules with the next unused ID; retired rules are marked `status: retired`, never deleted or renumbered.
- Always read the existing artifact first to recover IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits the workload directly, and the policy is complete without any sibling artifact.

**Bridges in (optional, opt-in):** `./agentic-artifacts/shape-decision.md` (from `agent-shape-selector`). If present at that canonical path, offer to seed the workload inventory from its roles and model-tier assignments — use it only if it exists at that canonical path **and** the user confirms. If absent or declined, elicit the inventory manually; completeness is unaffected.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `handoff-ticket-designer` and `trust-verification-architect` as consumers of this policy. Offer, never auto-run. The policy must be fully usable if every bridge is declined.
