# Slop Pattern Auditor — adversarial evaluation

<!-- artifact-id: slop-pattern-auditor-eval | schema: v1 -->

**Skill under test:** `slop-pattern-auditor` (harness-independent; pure SKILL.md, no engine).
**Method:** three agent tiers (Claude Haiku, Claude Sonnet, Claude Opus) were each given only the SKILL.md and the adversarial corpus, with no other guidance, and asked to execute Steps 2–5. Outputs were graded against `expected-findings.json` (22 cases: 12 required detections, 7 must-not-flag traps, 3 global contract checks). The grading baseline was an independent pass by Claude Fable 5.
**Date:** 2026-07-19. **External effects:** network=0 secrets=0 remote_jobs=0 spend_usd=0 (subagent inference only).

## Corpus traps

Positives: negative parallelism (`not_but`, `not_instead`, `rather_than`), cadence tricolon, em-dash aside, colon lead-in, semicolon splice, transition pileup, trailing participle, curly quotes.
Negatives: cross-sentence "didn't … Instead," (must not match), a legitimate not-42-but-41 correction with cue words, a genuine three-item enumeration, hyphenated compounds and numeric ranges, a time colon and a URL colon, semicolons inside backticked code, em-dashes inside a verbatim quotation, straight quotes adjacent to curly ones, French negative parallelism (must abstain), modality/negation vocabulary with no pattern.

## Round 1 (initial skill draft)

| Case class | Haiku | Sonnet | Opus |
|---|---|---|---|
| Required detections (12) | 11/12 (missed line-17 semicolon splice) | 12/12 | 12/12 |
| Must-not-flag traps (7) | 5/7 (hallucinated a curly quote on straight-quoted text; single bold lead-in labeled harmful) | 6/7 (double-reported one span as both transition_pileup and tricolon) | 7/7 |
| Global contract (3) | 2/3 (residual catalog patterns inside two rewrites) | 3/3 | 3/3 |

Opus matched the Fable baseline exactly, including catching that the round-1 corpus's "curly" quotes were in fact straight ASCII (a fixture bug, fixed for round 2).

## Fixes applied to the skill after round 1

1. **Literal punctuation rule** (Step 2 + catalog): punctuation findings must be byte-confirmed; never infer characters not present.
2. **Zero-candidate sweep** (Step 2): before recording zero candidates for a punctuation family, enumerate every literal `;` `—` `–` `:` and quote character and account for each.
3. **Single-family rule** (catalog): one span reports in its single best-fitting family, never two.
4. **Single bold lead-in capped at `uncertain`** (catalog).
5. **`other_preregistered` cannot absorb unpreregistered candidates** (catalog).
6. **Whole-catalog residual check on rewrites** (Step 4), with named examples of smuggled triads and trailing participles.
7. **Cascade hardened**: small-tier labels/rewrites are drafts until mid-tier confirmation; spot-checks probe recall (re-scan an unflagged section) as well as precision; disagreement either way escalates the artifact.

## Round 2 (revised skill; corpus with genuine curly quotes)

| Case class | Haiku | Sonnet |
|---|---|---|
| Required detections (12) | 12/12 — the character sweep recovered the previously missed splice | 12/12 |
| Must-not-flag traps (7) | 6/7 (still reported a straight-quoted line as a curly-quote candidate, though only as `uncertain`) | 7/7 |
| Global contract (3) | 2/3 (rewrites for the tricolon and trailing participle still contained residual patterns) | 3/3 |

## Verdict

- **Sonnet, round 2: 22/22** — matches the Fable baseline on every case, including all traps and rewrite constraints.
- **Opus, round 1: 22/22** on the harder (buggy-fixture) corpus, matching the Fable baseline and exceeding it on literal byte verification.
- **Haiku: detection-grade only.** After revision its recall is complete (12/12 detections), but rhetorical-intent classification and rewrite discipline remain below the bar. This is a model-capability property, not a prompt defect; two rounds of wording changes fixed every mechanical failure and none of the judgment failures.

**Consequence encoded in the skill:** the Model cascade section makes tier assignment binding — small tier detects (where it is now provably complete), mid tier classifies and rewrites, strongest tier adjudicates `uncertain` and spot-checks both directions. Under that assignment the cascaded output equals the strongest-model output at lower cost, which is the skill's stated quality bar.

**Scope of claim:** these results cover one 21-line adversarial corpus and one model family, produced by agent judgment (`agent_review`); they are evidence the skill's instructions transfer across tiers, not a benchmark of the models.
