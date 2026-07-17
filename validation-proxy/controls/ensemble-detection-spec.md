# Ensemble Detection Specification

## Objective

Estimate proxy quality and risk using independent bias-only, quant-only, and combined detectors, then aggregate forecasts with correlation-adjusted uncertainty. The design uses CLT-style asymptotics only where diagnostics support them.

## Unit of analysis

One record is one passage-task-judge triple. Passage is the clustering unit for uncertainty; judge family is a second clustering dimension. Multiple prompt variants from one model family are correlated measurements, not independent people.

## Judge panel

- At least five genuinely distinct evaluator ancestry/provider families; methodology variants are nested within ancestry family.
- The currently proposed seven evaluator implementations collapse to approximately three ancestry clusters and therefore do not yet satisfy this requirement.
- Each passage receives all available judgments under opaque randomized IDs.
- No judge sees another judgment, aggregate, generator identity, or source condition.
- A generator family cannot judge its own outputs.
- Forecasts are collected before any discussion or aggregate exposure.

## Independence and effective sample size

For equal-variance exchangeable errors:

```text
n_eff = n / (1 + (n - 1) * rho_bar)
SE_corr = SE_iid * sqrt(1 + (n - 1) * rho_bar)
```

Estimate `rho_bar` from residual agreement after removing passage difficulty and domain effects. Report raw `n`, `rho_bar`, `n_eff`, design effect, and family-level correlations. If `n_eff < 4`, label the ensemble inconclusive. Increasing prompt variants inside one family is not an acceptable repair; add a genuinely different family or evidence source.

## Three detector passes

1. **B pass:** bias/process detector emits catalog flags without performance scores.
2. **Q pass:** quantitative detector computes scoring, calibration, dependence, uncertainty, and influence diagnostics without bias labels.
3. **C pass:** interaction detector consumes frozen B/Q records and applies C1-C15 and UC1-UC5 rules.

All three pass records are immutable and hashed before fusion.

## Estimation

- Binary rates: equal-family-weighted estimate plus Wilson interval.
- Primary uncertainty: two-way cluster bootstrap by passage and judge family, 10,000 resamples, seed `20260712`.
- Domain estimates: executive/corporate communications, marketing/editorial, and technical/scientific documentation reported separately.
- Overall estimate: equal domain weights, preventing the largest domain from dominating.
- Calibration: out-of-fold only; report Brier score, Brier skill, log score, ECE, MCE, reliability/resolution/uncertainty.
- Model selection: no threshold, weight, or recalibration change after unblinding.

## Decision logic

Benefit thresholds pass only when the lower 95% bound meets the threshold. Harm ceilings pass only when the upper 95% bound stays below the ceiling. Automatic failures override averages and confidence intervals.

Combined evidence states:

- Bias-only detection: `B >= tB`, Q/C below threshold.
- Quant-only detection: `Q >= tQ`, B/C below threshold.
- Combined detection: `C >= tC`, or at least two channels exceed threshold.
- Conflict: one channel passes and another blocks; route to review.
- Insufficient independence: `n_eff < 4`; result inconclusive.

Thresholds `tB`, `tQ`, and `tC` must be selected on training data and frozen before Gate B evaluation.

## Sensitivity and bias controls

- Leave-one-model-family-out estimates.
- Leave-one-domain-out estimates.
- Worst-family and worst-domain result.
- Equal-family versus Brier-skill-shrunk weights.
- Pre/post aggregate-exposure variance to detect herding.
- Frame reversal and evidence-order reversal.
- Counterfactual disconfirmation challenge.
- Null-model and reference-class comparison.
- Copula/dependence diagnostic for tail agreement.
- Conformal empirical coverage.
- CDA content-fixed/length-divergent and length-fixed/content-divergent pairs.
- MUSE uncertainty-versus-conformity decomposition with calibrated uncertainty.
- Expanded structural ontology for tricolons, trailing participle clauses, em dashes, curly quotes, transition pileups, and bold lead-in lists.
- Semantic-necessity labels so stylistic presence is not automatically treated as failure.

## Output contract

Every result includes raw count, effective count, correlation matrix hash, estimate, 95% interval, domain/family strata, B/Q/C channel values, Clarvoy flags, automatic failures, evidence grade, policy version, and `PROXY - NOT REAL-USER VALIDATION` banner.
