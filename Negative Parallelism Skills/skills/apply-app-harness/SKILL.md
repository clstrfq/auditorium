---
name: apply-app-harness
description: Apply the reusable evidence harness to any app repository. Use whenever building, changing, reviewing, evaluating, or releasing an app; when the user asks for a trustworthy build, acceptance proof, replayable receipt, AI-output quality check, negative-parallelism check, or the same harness across projects; and when any coding agent (Codex, Claude Code, Cursor, Gemini CLI, or an AGENTS.md agent) should install or mimic the harness workflow. Idempotent — re-running against unchanged inputs reuses the existing packet instead of writing a duplicate.
---

# Apply App Harness

Run one consistent seven-step loop: contract, inspect, change, verify, attribute, receipt, self-verify. Keep engineering completion strictly distinct from empirical or product claims.

> **Portable skill.** One canonical file, installed byte-identically into every agent surface (`.codex/skills/`, `.claude/skills/`, `.cursor/skills/`, `.gemini/skills/`, `.agents/skills/`). The workflow must not drift between hosts. Uses only standard file operations and the local launcher; it makes no network call, reads no secret, submits no cluster job, and spends nothing.

## Find or install the launcher

1. Prefer `./tools/app-harness` when it exists.
2. Otherwise use `${APP_HARNESS_HOME}/harness` when `APP_HARNESS_HOME` is set.
3. Otherwise ask the user for the harness engine root; do not guess a path.
4. To install: run `<launcher> install <project-root>` (add `--surface all` for every agent surface, or repeat `--surface <key>`), then read `.app-harness/contract.json` before continuing.
5. Never overwrite a conflicting installation without the user's explicit `--force` direction.

Discover what a given engine supports with `<launcher> surfaces` and `<launcher> models`.

## Workflow

Follow these steps in order. Each writes auditable content to a file; none depends on chat history surviving.

### Step 1 — Contract

State the app job, user, smallest input, primary output, scope cap, exclusions, and success proof in a compact working note. Read `.app-harness/contract.json` when present and treat it as authoritative for installation facts. Make only reversible assumptions that do not materially change the product. Record every assumption explicitly — an unrecorded assumption is the most common source of a false receipt.

### Step 2 — Inspect

Read the existing code, tests, repository instructions, and current state. Identify the earliest layer responsible for the requested behavior. Preserve unrelated work and source data. Note what you did **not** read; scope of inspection is part of the evidence.

### Step 3 — Change

Implement the smallest contract-complete slice. Keep external effects, credentials, deployment, publication, and spending outside scope unless the user explicitly requests them. Never manufacture receipts for actions that did not occur.

### Step 4 — Verify

Run the repository's relevant tests and inspect real output. When the app produces prose or model responses, save a representative TXT, MD, CSV, JSONL, or NDJSON artifact and run:

```bash
./tools/app-harness analyze <artifact>
```

Treat `harmful`, `legitimate`, and `uncertain` findings differently. Suggest non-destructive rewrites only for harmful findings. Preserve numbers, names, citations, modality, URLs, and negation scope. Never auto-accept uncertain findings or overwrite source text.

If the deterministic launcher is unavailable, mimic the same review manually and label it `agent_review`, not a deterministic harness result. This distinction is not cosmetic: a deterministic result is replayable and an agent judgment is not. **Hook — standardized manual review:** run the `slop-pattern-auditor` skill against the artifact for this fallback rather than improvising a review; it defines the same harmful/legitimate/uncertain rubric and the `agent_review` label independently, so the fallback stays consistent across every app that uses this skill. This hook is opt-in — `slop-pattern-auditor` runs standalone and this skill's Step 4 is complete without it, using its own bare rubric above.

### Step 5 — Attribute

Record which model produced any analyzed text, using `<launcher> models` for the registered families (Llama, Mistral, Qwen, DeepSeek, Gemma, Gemini, ChatGLM, GPT, Claude). Rules:

- An identifier matching no family is `unattributed`. Never guess a lineage.
- An identifier naming two real lineages (for example a DeepSeek distillation of a Qwen base) is `ambiguous`, not one of the two. Do not collapse it.
- Attribution is provenance only. It never asserts that a model was executed, fine-tuned, or benchmarked here.

Use `not_applicable` when the app produces no natural-language output.

### Step 6 — Receipt

When `app-harness analyze` is the whole job, use the packet's generated `receipt.json`; do not create a duplicate receipt. For a broader app build, write or update one machine-readable build receipt under `.app-harness/receipts/` and reference any analyzer receipt from it. Record input and artifact hashes, tests actually run, output inspection, model attribution, unresolved items, and external effects. Use `not_evaluated` when evidence is absent — never `pass`.

End every receipt-bearing report with the `## Next steps` block from the output template.

Apply this evidence vocabulary when creating or validating a project contract or receipt:

- `measured` — produced by an executed test or an inspected artifact.
- `corroborated` — supported by a separate attributable source with a scoped relationship.
- `agent_review` — generated by an agent without deterministic execution.
- `not_evaluated` — no sufficient evidence was produced.
- `not_applicable` — the criterion does not apply to this app or change.

A minimum receipt carries `schema_version`, `status` (`pass|fail|inconclusive`), `job`, `input_hashes`, `artifacts`, `tests`, `ai_output_review`, `unresolved`, and `external_effects` (`network_calls`, `secrets_accessed`, `remote_jobs_submitted`, `external_spend_usd`, each `0` unless the user explicitly authorized otherwise). Use content hashes for replayable identity — a timestamp may describe a run but must never be the only identity key. Generated fixtures can prove code paths and invariants; they cannot establish human preference, product demand, production performance, or transfer to an inaccessible model. If an installed `.app-harness/contract.json` is present, treat it as authoritative for installation facts (schema/harness versions, project root, skill locations, supported formats, source-preservation and uncertain-review rules, default external-effects policy) and extend it under a `project` key rather than deleting installation fields; do not let it become a second PRD.

### Step 7 — Self-verify

Before finishing, check your own work and fix anything that fails:

- The primary artifact and receipt exist at their stated paths, and every path you cite resolves.
- The source file is byte-unchanged (compare its hash to the receipt's input hash).
- Tests listed in the receipt were actually run — no test is listed from memory or intention.
- Every `pass` is backed by observed output; absent evidence reads `not_evaluated`, not `pass`.
- Model attribution is present, with `unattributed`/`ambiguous` preserved rather than resolved by guess.
- `external_effects` counters reflect reality (all zero unless the user explicitly authorized otherwise).
- IDs are stable and the change log reflects reality (see idempotency contract).
- The report ends with the `## Next steps` block.

Report the verification result to the user as a short pass/fail list. If a check fails and you cannot fix it, say so plainly rather than shipping a receipt that overstates.

## Output template

```markdown
# App Harness Report
<!-- artifact-id: app-harness-report | schema: v1 -->

## AH-NNN: <job name>
- Status: pass | fail | inconclusive
- Job: <short concrete job>
- Contract assumptions: <reversible assumptions made>
- Inspected: <what was read> | Not inspected: <what was not>
- Change: <smallest contract-complete slice delivered>
- Tests actually run: <command → result>
- AI output review: pass | fail | not_applicable | not_evaluated | agent_review
- Model attribution: <family | unattributed | ambiguous(a,b) | not_applicable>
- Artifacts: <path> (sha256: <hash>)
- Receipt: <path>
- External effects: network=0 secrets=0 remote_jobs=0 spend_usd=0
- Unresolved: <what remains open>

## Change log
- v1 (YYYY-MM-DD): initial report

## Next steps
Optional downstream skills (this report is complete without them):
- trust-verification-architect — add verification gates where failure cost is high
- model-routing-economist — cost out the model tiers behind this app's inference
- handoff-ticket-designer — design tickets if this build hands work between agents
- agent-memory-architect — persist unresolved items and receipt history across a multi-cycle build
```

## Idempotency contract

- **Unchanged inputs → identical output.** Re-running `analyze` on byte-identical source produces a byte-identical packet: the runner detects the existing run and reports `reused`. The report body carries no run timestamps, so an unchanged re-run adds no change-log entry and rewrites nothing.
- **Changed inputs → in-place update.** The same job keeps its `AH-NNN` ID; fields update in place and one dated change-log entry records the delta (e.g., "v2: added CSV path → 3 new findings"). Never write `app-harness-report-v2.md`, `receipt (1).json`, or any duplicate file.
- **New job → new record.** Append a new `AH-NNN` section with the next unused number; never renumber existing records.
- **Installation is idempotent.** `install` reports `unchanged` for byte-identical artifacts and refuses a conflicting overwrite unless the user passes `--force`.
- Always read the existing report and receipt first to recover IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits the contract directly from the user, and the report plus receipt are complete without any sibling artifact.

**Bridges in (optional, opt-in):** `./agentic-artifacts/trust-architecture.md` (from `trust-verification-architect`). If present at that canonical path, offer to align Step 4's verification with its declared gates and Step 6's receipt with its citation contracts — use it only if it exists at that canonical path **and** the user confirms. If absent or declined, verify from the contract alone; completeness is unaffected. **Hook (Step 4):** `slop-pattern-auditor`'s report, described above, when the deterministic launcher is unavailable — opt-in and only as the fallback review method, never required.

**Bridges out (optional, opt-in):** the `## Next steps` block offers `trust-verification-architect` (consumes this report's unresolved items to place gates), `model-routing-economist` (consumes the model attribution to build a cost model), `handoff-ticket-designer` (consumes the workflow if this build spans multiple agents), and `agent-memory-architect` (consumes a long-running build's unresolved items and receipt history as a durable `state.md`/`decisions.md` store, so a multi-cycle build does not re-derive its own history each session). Offer these; never auto-run them. The report and receipt must be complete and useful even if every bridge is declined.

## Finish

Lead with the actual outcome. Link the primary artifact and receipt. State remaining limits in one short paragraph. Do not claim production readiness, empirical efficacy, user demand, or external execution from generated fixtures or agent judgment alone.
