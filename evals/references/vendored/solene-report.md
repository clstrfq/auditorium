# Solene Layer-2 comparative eval — gpt-5.6-sol

Run date: 2026-07-11 EDT (2026-07-12 UTC)

## Decision

The Codex comparative gate passed, with no observed classification errors on
the 48-case held-out split. This is strong conformance evidence for the
synthetic corpus, but it is **not production-grade proof and not evidence that
Codex can replace the production Anthropic classifier**. The held-out set is
small, the Codex agent runtime differs from the production API request, and the
95% Wilson lower bounds remain below the 0.90 gate targets.

## Frozen inputs and runtime

- Base commit before this eval work: `1d45b14cebb9d68720394d1ad718c44baf4df2d6`
- Model: `gpt-5.6-sol`, reasoning effort `low`
- Runtime: `codex-cli 0.144.0-alpha.4`
- Production comparison model (unchanged): `claude-haiku-4-5`
- Production prompt SHA-256: `9a8803e6ea9e1fb39cbfa3618ae62d53dc39ceeb0831c640e2a35365af776a4f`
- Dev dataset SHA-256: `62c05caf730af8324d9cc806cd18e74db0b3fcfdf517ef252c0f89f7901bd538`
- Test dataset SHA-256: `5ed5c0c1065aa1ee4ff60199b673239b203171cd7f4cb75aff802864bc917706`
- Output schema SHA-256: `14cab9ad3523bcad50eb04587a2a6d00b9fe2c7d2f82df106820c012e04d8dc5`
- Cache contract: `2026-07-12.1`; 132 entries; exact-text, schema,
  wrapper, reasoning-effort, and CLI-version fingerprinted
- Cache SHA-256 after rekeying: `4286709251b4d066e2dd973b96bc063d204a85c9b1d86504178427acd0dd93ff`

The gold corpus grew from 120 to 144 synthetic cases. Twenty-four cases were
added only to dev (12 transactional and 12 benign); the 48-case test split was
not edited. A blind metadata/label review accepted 23 additions unchanged and
corrected `L2-DEV-082` from decorative `emoji` obfuscation to `none` without
changing its text or label.

## Invocation method

Each non-Layer-1 case ran in its own ephemeral, read-only Codex CLI session.
The production classifier policy was extracted from the edge-function source,
combined with the exact synthetic user text, and constrained by a JSON output
schema. Tools or invalid output fail closed. Calls were checkpointed to the
provider-specific cache and metered under a pre-call reservation budget.

This is an agent-runtime comparison. Unlike production, the classifier policy
cannot be supplied as an API `system` role through this CLI path; it is part of
the Codex instruction beneath Codex's own agent system layer. The roughly
13,600 input tokens per short case make that wrapper effect material.

## Results

| Split | Cases | Live Layer-2 calls | TP | FN | FP | TN | TPR | TNR | Recorded tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dev | 96 | 88 | 50 | 0 | 0 | 46 | 100% | 100% | 1,196,165 |
| Held-out test | 48 | 44 | 24 | 0 | 0 | 24 | 100% | 100% | 598,001 |
| Combined replay | 144 | 132 cached | 74 | 0 | 0 | 70 | 100% | 100% | 1,794,166 source tokens |

Held-out test checks:

- Coverage: 100%
- Accuracy and precision: 100%
- Unparseable or invalid verdicts: 0
- Layer-1 precedence: intact
- Gate thresholds: passed on point estimates
- Pipeline TPR/TNR Wilson 95% intervals: `[86.2%, 100%]` for each
- Codex-only transactional TPR after excluding four Layer-1 catches:
  20/20, Wilson lower bound approximately 83.9%
- Model confidence range across all 132 calls: 0.96–1.00
- Transactional cases above the 0.8 auto-suspend threshold: 100%
- Failing cases: none observed

The deterministic `npm run eval:codex:ci` replay reproduced the held-out
matrix and gate with zero additional model calls.

## Validity limits

1. The gate checks point rates, not confidence-interval lower bounds. The
   held-out result therefore does not establish TPR or TNR ≥0.90 with 95%
   confidence.
2. The synthetic dev and test splits contain close semantic families. They are
   not a substitute for independently authored, blind holdout cases or
   consented production-pattern abstractions.
3. Codex confidence is saturated and has no evidence near the 0.8 decision
   boundary; the production threshold is not calibrated for this model.
4. There was one live sample per case. Replay proves cache determinism, not
   live-model determinism.
5. The production Anthropic verdict cache remains separate and empty. This run
   does not arm `npm run eval:ci`.

## Next evidence needed

- Create a new independently authored test tranche with no semantic twins and
  at least 35 Layer-2 cases per class; with zero errors, 35/35 is the minimum
  sample whose Wilson lower bound clears 0.90.
- Blind-review those gold labels before any model sees them.
- Add genuinely ambiguous boundary cases and repeated live trials to measure
  confidence calibration and run-to-run variance.
- If Codex is considered for production, evaluate a direct API request with
  separate system/user roles rather than treating this CLI result as a proxy.
