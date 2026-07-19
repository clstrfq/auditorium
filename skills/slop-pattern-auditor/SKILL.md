---
name: slop-pattern-auditor
description: Flag formulaic AI-writing patterns in any text artifact without any engine or launcher installed — negative parallelism ("not X but Y", "not X, instead Y", "rather than"), triplicate reasoning (tricolons, rule-of-three framing), em-dashes and other connector dashes, colon lead-ins, semicolon splices, trailing participles, curly quotes, transition pileups, and bold lead-ins — then classify each finding harmful/legitimate/uncertain and propose fact-preserving rewrites for harmful ones. Use whenever a user asks to check text for AI tells, slop, negative parallelism, em-dash overuse, "make this sound less like AI", review model output quality, or audit a doc/README/report/JSONL of generations. Works in Codex, Claude, or any agent host; pure judgment workflow labeled agent_review. Idempotent — re-running on unchanged input reproduces the identical report instead of writing a duplicate.
---

# Slop Pattern Auditor

> **Claude skill.** Install this file as `~/.claude/skills/slop-pattern-auditor/SKILL.md` for personal use, or keep it in-repo at `.claude/skills/slop-pattern-auditor/SKILL.md` so the whole project shares it. Invoke it as `/slop-pattern-auditor`. Uses only standard file operations; artifacts are written relative to the repository root. Makes no network call, reads no secret, and spends nothing.

Audit any Markdown, text, CSV, or JSONL artifact for the formulaic patterns that mark machine-generated prose, using nothing but this file and ordinary file reads. This skill is the harness-independent form of a deterministic review engine: the detection rules, rubric, and rewrite constraints below reproduce that engine's behavior, but the results here are produced by agent judgment. Label them **`agent_review`**, never as a deterministic result — a deterministic result is replayable and an agent judgment is not. Never modify the source artifact; the audit proposes, a human disposes.

## Pattern catalog

Detect these families, in document order. Within one family, overlapping matches count once (keep the leftmost), and one span counts in the single best-fitting family — never report the same rhetorical phenomenon under two families. Record each finding's family, exact matched text, and enclosing sentence. Punctuation findings must be literal: confirm the exact character is present (curly “ vs straight ", em-dash — vs hyphen -) by re-reading or byte-checking; never infer punctuation that is not in the bytes.

| Family | Flag when | Do NOT flag |
|---|---|---|
| `negative_parallelism` | A single sentence pairs a negation with a pivot: "not X but Y" (rule `not_but`), "not X … instead Y" (rule `not_instead`), or "rather than X" (rule `rather_than`), with the negation and pivot within ~160 characters / ~30 words of each other | "not only … but also"; negation and pivot in different sentences; a span exceeding ~160 characters / ~30 words is `uncertain`, not dropped |
| `tricolon` | Rhetorical rule-of-three framing: three parallel clauses or adjectives deployed for cadence ("fast, simple, and reliable"), triadic sentence runs, three-bullet emphasis | A genuine enumeration: removing or reordering any one item changes the sentence's factual claim (distinct referents — named parts, people, cited results). Cadence-driven items are near-synonyms or could be cut to one or two without losing information; when the test doesn't clearly resolve either way, `uncertain` |
| `em_dash` | Em-dash (—), en-dash (–), or spaced hyphen (" - ") used as a clause connector or dramatic aside | Hyphenated compounds ("state-of-the-art"), numeric ranges ("pp. 3–7"), minus signs, dashes inside verbatim quotations or code |
| `colon_lead_in` | A short dramatic setup resolved by a colon ("The verdict: ship it.") and header-style lead-ins in prose | Times ("3:30"), ratios, URLs, key: value data, list introductions before an actual list, titles |
| `semicolon_splice` | Semicolon joining two independent clauses for rhetorical balance | Semicolons in code, in citations, or separating list items that contain commas |
| `trailing_participle` | Sentence-final participial clause appended for gravitas (", highlighting …", ", underscoring …", ", showcasing …") | Load-bearing = the clause states a fact not recoverable from the main clause (a number, a named consequence, a new entity). A clause that only restates, editorializes, or gestures at significance ("highlighting", "underscoring", "showcasing", "demonstrating the importance of") is not load-bearing |
| `curly_quote` | Typographic quotes (" " ' ') in plain technical text | Typographically curated prose where curly quotes are the document's own consistent style |
| `transition_pileup` | Two or more stacked discourse markers opening consecutive sentences or one sentence ("However, … Moreover, … Furthermore, …") | A single transition doing real logical work |
| `bold_lead_in` | Three or more "**Label:** text" paragraph or bullet openers in one document, repeated as a formula | Fewer than three occurrences (at most `uncertain`, never `harmful`); a document's declared glossary/definition format |
| `other_preregistered` | Any additional pattern the user names before the audit starts (record the definition in the report) | Anything not agreed before detection began — a candidate fitting no family goes in its best-fitting real family or is dropped, never parked here |

## Classification rubric

Classify every finding `harmful`, `legitimate`, or `uncertain`; the abstain label is `uncertain`, and any doubt abstains. Every negative-parallelism pivot asserts *some* distinction between X and Y — that alone never makes it `legitimate`. The operational test: does the sentence correct a belief a reasonable reader would otherwise hold, or would prepending "contrary to what you might assume" preserve its meaning? If X is a plausible prior the sentence is disproving, it's a correction. If X is a rhetorical foil chosen for rhythm rather than something anyone would have believed, it's formulaic. Confidence and this test are independent: the confidence gate below decides whether to abstain at all; once above it, the correction test alone decides `harmful` vs. `legitimate`, never confidence.

- `legitimate` requires a real correction by the test above, or is verbatim quotation, code, or data, or is syntactically required. State the disproved prior (or the syntactic requirement) in one sentence — not just that a "distinction" exists.
- `harmful` is formulaic rhetorical use: the pivot fails the correction test above, cadence-driven triads, connector dashes replacing precise syntax. State which formula it matches.
- `uncertain` whenever confidence is below roughly 0.7, the context is not predominantly English, or the correction test does not resolve cleanly either way. Uncertain findings are never auto-accepted and never rewritten without an explicit user selection recorded in the report.

## Model cascade

When the host can delegate to model tiers, run detection (mechanical catalog matching) on a small fast model, classification on a mid-tier model, and reserve the strongest available model for adjudicating `uncertain` findings and spot-checking at least one in five of the others. Spot-checks must probe both directions: confirm flagged findings are real (precision) **and** re-scan at least one unflagged section for missed candidates (recall) — small models miss quiet patterns like an unbalanced semicolon splice more often than they invent loud ones. Escalate the whole artifact if a spot-check disagrees either way. Tier assignment is binding, not advisory: a small-tier label or rewrite is a draft until a mid-tier model confirms it, because small models reliably find enumerable punctuation yet misjudge rhetorical intent and smuggle catalog patterns into their own rewrites. The quality bar is fixed: the cascaded result must match what the strongest available model would produce alone; if the host has no tiers, one model performs every step. The cascade changes cost, never the rubric. Which concrete model sits in which tier changes over time and by vendor; bind that mapping in the project README, not in this file.

## Workflow

Follow these steps in order. Each writes auditable content to a file; none depends on chat history surviving.

### Step 1 — Scope

Identify the artifact(s) to audit — here, "artifact" means the input text being examined, not this skill's own output (which is called a "report," never an artifact, throughout this file): a path, a pasted text (save it to a file first so the audit has a stable input), or a JSONL of model outputs. Record for each input its path and content fingerprint — sha256 when a shell is available, else byte length plus first and last 40 characters. Ask which optional families (`curly_quote`, `bold_lead_in`, `other_preregistered`) are in scope if the user has not said; default to all. Never audit text you were not pointed at, and never modify any input.

### Step 2 — Detect

Read the full input. Scan sentence by sentence against the pattern catalog and list every candidate in document order with: a candidate ID `<family>-<NNN>` numbered per family from 001, the exact matched text, the enclosing sentence, and the line number. Do not classify yet — detection is mechanical and over-inclusive by design; the "Do NOT flag" column is the only suppression applied here. Before recording zero candidates for a punctuation family, do a literal character sweep (find every `;`, `—`, `–`, `:`, `"`, `"`) and account for each occurrence — punctuation is enumerable, so a missed splice is a process failure, not a judgment call.

### Step 3 — Classify

Apply the classification rubric to each candidate in its enclosing sentence. Record label, confidence (0–1), and a one-sentence rationale of at most 240 characters. Non-English context or any classifier doubt yields `uncertain` with the rationale "human adjudication required". Report counts per family and per label.

### Step 4 — Rewrite

For each `harmful` finding (and only for an `uncertain` one the user explicitly selects, recording who selected it and why), propose **at least two distinct** rewrites of the enclosing sentence. Every proposal must pass all of these checks, and a proposal that fails any check is blocked, not repaired silently:

1. **Protected content** — numbers, percentages, URLs, citations, proper nouns, modal verbs (must/shall/should/may/might/can/could/will/would), and negation scope (never/cannot/must not …) appear in the rewrite exactly as in the source sentence.
2. **No residual pattern** — the rewrite contains no catalog pattern itself; check the whole catalog, not just the family being fixed (a rewrite of a negative parallelism that ends in a trailing participle, smuggles in a triad, or keeps curly quotes is blocked).
3. **Length** — non-empty and at most 2.5× the source sentence length.
4. **Fidelity** — at least half the source's content words survive; when they do not, mark the proposal `semantic_fidelity_uncertain` and block it.
5. **Variety** — no two proposals in the same report open with the same first four words.

Rewrites are proposals recorded in the report; never apply one to the source file.

### Step 5 — Attribute

Record what produced the audited text when the user or the data says so (a `model` field, a stated generator). An identifier matching no known model lineage is `unattributed` — never guess. An identifier naming two real lineages (a distillation of another family's base) is `ambiguous`, listing both — never collapse it. Use `not_applicable` for human-written or unknown-origin text offered without provenance. Attribution is provenance only; it never asserts a model was executed or benchmarked here.

### Step 6 — Report

Write or update the single canonical report at `./agentic-artifacts/slop-pattern-review.md` using the output template. Each audited artifact gets one `SPA-NNN` record keyed by its path and fingerprint. Include the finding table, rewrite proposals, attribution, the review-mode label `agent_review`, and external effects (all zero: this skill makes no network call, reads no secret, submits no job, spends nothing).

### Step 7 — Self-verify

Before finishing, check your own work and fix what fails:

- The report exists at its canonical path and every path cited in it resolves.
- Every source input is byte-unchanged (fingerprint matches Step 1).
- Every finding cites text that actually occurs at the stated location — re-read and confirm at least every `harmful` finding.
- Every `harmful` label has a formula named; every `legitimate` label has a material reason; every low-confidence or non-English case reads `uncertain`.
- Each rewrite proposal passes the five Step 4 checks; blocked proposals say why.
- Review mode reads `agent_review`; attribution preserves `unattributed`/`ambiguous` rather than resolving them by guess.
- IDs are stable and the change log reflects reality (see idempotency contract).
- The report ends with the `## Next steps` block.

Report the result to the user as a short pass/fail list. If a check fails and cannot be fixed, say so plainly rather than shipping a report that overstates.

## Output template

```markdown
# Slop Pattern Review
<!-- artifact-id: slop-pattern-review | schema: v1 -->

## SPA-NNN: <artifact path or name>
- Review mode: agent_review
- Input: <path> (<sha256 or fingerprint>)
- Families in scope: <list>
- Findings: <N> (harmful <n> / legitimate <n> / uncertain <n>)

| ID | Family | Line | Matched text | Label | Conf. | Rationale |
|---|---|---|---|---|---|---|
| negative_parallelism-001 | negative_parallelism | 12 | "not speed but correctness" | harmful | 0.85 | Fails the correction test: no reader plausibly assumed speed was the goal; "speed" is a rhetorical foil for rhythm, not a disproved belief. |

### Rewrites (harmful + user-selected uncertain only)
- negative_parallelism-001:
  1. "<proposal>" — checks: pass
  2. "<proposal>" — checks: pass
- <ID>: blocked — <blocking reason>

### Attribution
- <model family | unattributed | ambiguous(a,b) | not_applicable>

- External effects: network=0 secrets=0 remote_jobs=0 spend_usd=0
- Unresolved: <uncertain findings awaiting human adjudication>

## Change log
- v1 (YYYY-MM-DD): initial review

## Next steps
Optional downstream skills (this report is complete without them):
- apply-app-harness — replay this audit deterministically when the review engine is installed, or use this report as its standardized manual-review fallback
- trust-verification-architect — add verification gates where flagged text ships to users, seeded from this report's harmful/uncertain counts
- model-routing-economist — weigh a model family's harmful-finding rate as one input to tier assignment
- qa-companion — audited surfaces here become UX probe targets for that skill's novice/expert path tests
```

## Idempotency contract

- **Unchanged inputs → identical output.** Re-auditing a byte-identical artifact reproduces the same findings, IDs, labels, and proposals; the report body carries no run timestamps, so nothing is rewritten and no change-log entry is added.
- **Changed inputs → in-place update.** The same artifact keeps its `SPA-NNN` ID; the finding table updates in place and one dated change-log entry records the delta (e.g., "v2: source revised → 2 findings resolved, 1 new"). Never write `slop-pattern-review-v2.md`, `review (1).md`, or any duplicate file.
- **New artifact → new record.** Append the next unused `SPA-NNN`; never renumber existing records. Candidate IDs restart per record, not globally.
- Always read the existing report first to recover IDs and version numbers.

## Standalone operation and bridges

This skill runs fully standalone: Step 1 elicits its inputs directly from the user, and the report is complete without any engine, launcher, sibling skill, or network access.

**Bridges in (optional, opt-in):** a deterministic review engine at `./tools/app-harness`. If present, offer to also run `./tools/app-harness analyze <artifact>` and record both results side by side, keeping the deterministic packet and this `agent_review` report clearly distinguished — use it only if it exists **and** the user confirms. If absent or declined, this audit stands alone; completeness is unaffected.

**Bridges out (optional, opt-in):** the `## Next steps` block offers four consumers of this report. Offer these; never auto-run them. If declined or absent, proceed exactly as the standalone workflow above specifies — the report's completeness is unaffected either way.

- `apply-app-harness` — **Hook (its Step 4):** this skill is the named standardized method for that skill's manual-review fallback when its deterministic launcher is unavailable. When invoked for that purpose, use this skill's own workflow unmodified and hand back the resulting report; do not shortcut the rubric to fit the caller.
- `trust-verification-architect` — **Hook (its verification gates):** offer this report's `harmful` and `uncertain` counts, grouped by family, as candidate gate locations — a text surface with recurring `harmful` findings or an unresolved `uncertain` backlog is exactly the kind of high-failure-cost point that skill places gates around.
- `model-routing-economist` — **Hook (its workload inventory):** when this report's Step 5 attribution names a model family across multiple audited artifacts, offer the per-family `harmful`-finding rate as one input to that skill's model-tier assignment — a family with a persistently higher rate is weaker evidence for routing rote generation to it, not proof by itself.
- `qa-companion` — offer this report's audited surfaces as UX probe targets so its novice/expert path tests cover the same user-facing copy this audit flagged.

## Finish

Lead with the counts: findings by family and label, rewrites proposed, and what remains `uncertain` for a human. Link the report. State plainly that this was an `agent_review` — reproducible in method, not in bytes — and do not claim the audited text is free of any pattern outside the declared scope.
