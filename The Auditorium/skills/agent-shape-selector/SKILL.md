---
name: agent-shape-selector
description: Classify a task and select the right multi-agent topology ("agent shape") — Orchestrator-Worker, Pipeline, Debate/Review, Coordinated Stackelberg, or no agents at all — producing a file-based Shape Decision Record with rationale, role assignments, and risk notes. Use whenever a user asks "what agent shape/topology/architecture do I need", "should this be one agent or a team", "how should my agents be organized", "orchestrator vs pipeline", wants to run the 1-minute test on a task, or describes a workflow they want to automate with multiple AI agents but hasn't chosen a structure. Also trigger on vague requests like "design my agent team" or "is this even an AI task". Idempotent — re-runs update the existing decision record in place with versioned deltas.
---

# Agent Shape Selector

> **Claude skill.** Install this file as `~/.claude/skills/agent-shape-selector/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/agent-shape-selector/SKILL.md` so the whole project shares it. Invoke it as `/agent-shape-selector`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

Match a concrete task to the multi-agent topology that fits it, instead of defaulting to whatever architecture is fashionable. The efficiency and reliability of a multi-agent system depend on its "agent shape" — the structural hierarchy, delegation protocol, and communication pathways. Choosing wrong wastes tokens, overwhelms context windows, and produces unstable systems; choosing well isolates complexity and can cut costs by an order of magnitude (a premium orchestrator directing ~20 commodity workers has built entire web platforms for ~$8 in inference).

## Shape catalog

| Shape | Structure | Best for | Watch out for |
|---|---|---|---|
| **No AI / simple chat** | Human + single prompt | Tasks failing the 1-minute test for agent value | Over-automation of broken processes |
| **Single agent** | One model, tools, loop | Bounded tasks fitting one context window | Silent context overflow on long tasks |
| **Orchestrator-Worker** | Premium planner dispatches parallel commodity executors | Decomposable work with independent sub-tasks (large builds, research fan-out) | Sub-tasks that secretly depend on each other |
| **Gas Town variant** | Orchestrator plus dedicated monitor/integrity roles (Mayor / Polecats / Witnesses / Deacons) | Long-running fleets needing observability decoupled from planning | Role overhead on small jobs |
| **Pipeline** | Linear assembly line; each agent's output is the next agent's input | Unstructured→structured transforms, BI/ticket flows, compliance work needing step visibility | Any stage that needs to loop back |
| **Debate / Review** | Producer paired with adversarial critic | Subjective or high-stakes output where hallucination is costly | Critique loops that never converge — cap iterations |
| **Coordinated Stackelberg** | Asymmetric attacker/defender pair in a continuous loop | Security probing + self-hardening, any explore/remediate dynamic | Must be modeled at system level, not per-agent |

## Workflow

Follow these steps in order. Each produces auditable content in the output file.

### Step 1 — Elicit the task profile
Gather from the user (ask only for what's missing): the objective in one sentence; whether sub-tasks are independent, sequential, or adversarial; failure cost (what happens if the output is wrong); expected duration/recurrence; budget sensitivity; and compliance/visibility requirements. If the user pasted a task description, extract these and confirm rather than re-asking.

### Step 2 — Run the 1-minute test
Classify the task: could a competent human do it in under a minute with a search box? Then no agents — recommend simple chat or nothing. Is it bounded and single-context? Single agent. Only proceed to multi-agent shapes when the task genuinely exceeds one agent's cognitive breadth, tooling, or context window. Record the classification and reasoning verbatim in the decision record — this is the cheapest place to stop a bad build.

### Step 3 — Score candidate shapes
Score each catalog shape 1–5 against the task profile on: fit to dependency structure, failure-cost handling, debuggability, and cost profile. Present the top two candidates to the user with trade-offs before committing. Don't skip the runner-up: naming what you rejected and why is half the audit value.

### Step 4 — Specify the chosen shape
For the winner, define: each role (planner, workers, critic, monitor…), which model tier each role needs (premium reasoning vs. commodity execution — only the planning/goal-harness role usually needs the frontier model), the communication pathways between roles, parallelism limits, and iteration caps for any review loops.

### Step 5 — Write the Shape Decision Record
Write the artifact to the canonical path `./agentic-artifacts/shape-decision.md` using the output template below. Every decision gets a stable ID (`SD-001`, `SD-002`, …) that survives re-runs.

### Step 6 — Self-verify
Before finishing, check the written file and fix anything that fails:
- The file exists at the canonical path and parses as the template.
- Exactly one recommended shape, with at least one explicitly rejected alternative and rationale.
- Every role has a model tier assigned; every review loop has an iteration cap.
- The 1-minute test result is recorded, even if the answer was "multi-agent".
- IDs are stable and the change log reflects reality (see idempotency contract).
- The file ends with the `## Next steps` block.
Report the verification result to the user as a short pass/fail list.

## Output template

```markdown
# Shape Decision Record
<!-- artifact-id: shape-decision | schema: v1 -->

## SD-NNN: <task name>
- Status: recommended | superseded
- 1-minute test result: <no-AI | chat | single-agent | multi-agent> — <reasoning>
- Task profile: <objective, dependency structure, failure cost, duration, budget>
- Recommended shape: <shape> — <rationale>
- Rejected alternatives: <shape> — <why not>
- Roles: <role → model tier → responsibility>
- Communication pathways: <who hands what to whom>
- Iteration caps / parallelism limits: <values>
- Risks: <top 2–3 failure modes of this shape for this task>

## Change log
- v1 (YYYY-MM-DD): initial record

## Next steps
Optional downstream skills (each works without them):
- model-routing-economist — cost out the model-tier assignments above
- handoff-ticket-designer — design the tickets that move work between these roles
- trust-verification-architect — add verification gates where failure cost is high
```

## Idempotency contract

- **Unchanged inputs → identical output.** Re-running against the same task description must produce a byte-identical file: same IDs, same ordering, no new change-log entry, no run timestamps anywhere in the body.
- **Changed inputs → in-place update.** Keep the same `SD-NNN` ID for the same task; update fields in place and append one dated change-log entry describing the delta (e.g., "v2: failure cost raised → shape changed Pipeline → Debate/Review"). Never write `shape-decision-v2.md`, `shape-decision (1).md`, or any duplicate file.
- **New task → new record.** Append a new `SD-NNN` section in the same file with the next unused number; never renumber existing records.
- Before writing, always read the existing file (if any) to recover current IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: it elicits its own inputs in Step 1 and its deliverable is complete without any other artifact.

**Bridges in (optional, opt-in):** none. This skill is the natural entry point and consumes no sibling artifacts.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `model-routing-economist` (consumes `./agentic-artifacts/shape-decision.md` to build a cost model), `handoff-ticket-designer` (consumes it to derive ticket routes from the communication pathways), and `trust-verification-architect` (consumes it to place verification gates). Offer these; never auto-run them. A downstream skill may use this record only if it exists at the canonical path **and** the user confirms. The Shape Decision Record must be complete and useful even if every bridge is declined.
