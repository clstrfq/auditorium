# Clarvoy Control Crosswalk for Ensemble Forecasting

## Source status

- Role: control taxonomy and detector design reference
- Evidence status: supplied internal reference; not an empirical validation dataset
- Resolution: **vendored** — both the source document and its ingested Markdown are in
  `validation-proxy/controls/vendored/` and are checked by `scripts/verify_evidence.py`.
- Source content id: `sha256:a5da23aa01e4fa46027abb5fab1eea94c4af5ce194b2e3bbab92d019e145aa44`
- Ingested content id: `sha256:708807f31d57d991eebb98e6cc37bdfcf7797647f998d615645847ef7ca1110e`
- Baseline status: first recorded on 2026-07-17. Because no earlier hash existed, these
  ids establish the vendored baseline; they do not retroactively verify the bytes used
  before that date.

Origin, retained as provenance only and not as a dependency — these paths are where the
files sat on the authoring machine on 2026-07-12, and are not expected to resolve
anywhere else:

- Source: `Developer/Clarvoy/stable-dev/reports/clarvoy_bias_control_reference_catalog_pcc_forprofit.docx` (under the author's home directory)
- Ingested artifact: `Developer/Clarvoy/stable-dev/reports/_ingested/clarvoy_bias_control_reference_catalog_pcc_forprofit/content.md`

The source paths below remain provenance notes only. The authoritative identifiers and
repo-relative paths are registered in `evals/references/ftpo-evidence-catalog-1.1.0.json`.

## Detection channel B - bias and judgment-process risk

The bias-only channel produces a vector of flags and severities before it sees quantitative performance scores.

| Family | Catalog entries | Ensemble use |
|---|---|---|
| Probability/statistical reasoning | A1-A7 | Anchor shift, missing base rate, invalid conjunction, assumed independence, streak extrapolation, zero-risk distortion |
| Social influence | B1-B8 | Authority effects, bandwagon convergence, overconfidence, false consensus, groupthink, halo contamination |
| Action/economic preference | C1-C5 | Action bias, endowment, loss aversion, status quo, sunk-cost continuation |
| Evidence/narrative structure | D1-D6 | Confirmation, framing, hindsight, triviality, narrative closure, novelty preference |
| Cognitive processing | E1-E6 | Affect, knowledge asymmetry, empathy gap, information excess, planning fallacy, recency |
| Meta-bias | F1 | Bias-blind-spot risk and missing self-audit |
| Organizational learning | outcome/hindsight/memory entries | Retrospective rewriting, post-purchase rationalization, fading affect, peak-end/duration neglect, posterior-update error |

Required B-channel outputs per forecast:

- `bias_flags[]`: catalog ID, evidence span, direction, severity, confidence.
- `independence_controls`: blind-before-discussion, dissent captured, authority exposure order.
- `evidence_balance`: supporting vs disconfirming evidence coverage.
- `reference_class_status`: explicit/missing/misaligned.
- `retrospective_risk`: whether outcome knowledge contaminated the forecast record.

## Detection channel Q - quantitative forecast quality

The quant-only channel is computed without access to bias labels.

| Function | Catalog entries | Ensemble use |
|---|---|---|
| Proper scoring | Q1-Q8 | Brier, skill score, log/ignorance, CRPS, Bregman, quadratic and local proper scores |
| Calibration diagnostics | Q9-Q14 | ECE/MCE, Hosmer-Lemeshow extensions, Brier decomposition, Yates diagnostics |
| Recalibration | Q15-Q18 | Platt, isotonic, beta, spline/Bayesian calibration; fit on training folds only |
| Decision utility | Q19-Q21 | Cost-loss threshold, reference-class blending, posterior predictive checks |
| Dynamics/anomaly | Q22-Q26 | Zones, tipping/AR(1), influence Gini, cascade/snowball, coordination tax |
| Dependence/uncertainty | Q27-Q28 | Copula/dependence model and conformal coverage |
| Quant-field integrity | UQ1-UQ9 | Blind sample size, score spread, uniformity pressure, reviewer independence, evidence balance, processing completeness, phrase hits, challenge completeness, calibration error |

Required Q-channel outputs:

- Probability forecast and outcome when available.
- Brier/log score and skill relative to a preregistered baseline.
- Reliability, resolution, uncertainty, ECE/MCE, and calibration drift.
- Pairwise and family-level error correlation.
- Influence Gini and coordination/uniformity pressure.
- Conformal interval/set and empirical coverage.
- Reference-class and posterior-predictive checks.

## Detection channel C - bias/quant interactions

The combined channel receives only the frozen B and Q records, never raw judge identities.

| Combo | Catalog mapping | Trigger example |
|---|---|---|
| C1 | Planning fallacy | Optimistic duration plus weak reference-class uplift |
| C2 | Overconfidence/Dunning-Kruger | High confidence plus poor calibration record |
| C3 | Noisy expert override | Large expert deviation plus weak skill evidence |
| C4 | Authority/bandwagon/groupthink | High influence Gini plus compressed post-discussion variance |
| C5 | False consensus/halo | Uniform ratings across unrelated dimensions |
| C6 | Commission bias/optimism | Action preference despite negative cost-loss value |
| C7 | Anchoring | Estimate movement toward exposed first value beyond evidence update |
| C8 | Base-rate neglect/sample-size insensitivity | Strong posterior shift with weak N/reference class |
| C9-C10 | Dunning-Kruger/generalized overconfidence | Confidence exceeds calibrated resolution |
| C11 | Confirmation/framing | Evidence imbalance plus frame-sensitive forecast movement |
| C12 | Planning fallacy/groupthink | Shared optimistic timing with low independent variance |
| C13 | Narrative fallacy | Coherent story with weak posterior-predictive fit |
| C14 | Authority/bandwagon | Vote convergence tracks authority exposure order |
| C15 | Calibration-model overfit | In-sample calibration gain without held-out improvement |
| UC1-UC5 | Governance/learning combos | Deferential consensus, evidence echo, narrative lock-in, governance drift, learning washout |

## Fusion rule

The three channels remain separately reportable. Fusion cannot erase a channel failure.

```text
B = calibrated bias-risk probability
Q = calibrated quantitative-failure probability
C = calibrated interaction-risk probability

ensemble_risk = 1 - (1-B)^wB * (1-Q)^wQ * (1-C)^wC
```

Initial weights are equal (`wB = wQ = wC = 1/3`) because no outcome history supports skill weighting. After at least 100 resolved forecasts per channel, weights may be learned from out-of-fold Brier skill with shrinkage toward equal weights. Negative skill sets the channel weight to zero for decision fusion while its diagnostic output remains visible.

Decision states:

- `PASS`: no automatic failure; upper confidence bound below the preregistered risk threshold.
- `REVIEW`: interval crosses threshold, channels conflict, or effective ensemble size is inadequate.
- `BLOCK`: protected-fact/provenance failure, severe C-channel interaction, or lower confidence bound exceeds threshold.

## Clarvoy controls applied to CLT ensembles

- A1 Anchoring: collect every forecast blind before showing aggregates.
- A3/Q20 Base rates: require a reference class or label the forecast inside-view only.
- A5/Q27 Dependence: estimate error correlation and use effective sample size.
- B1/B7/Q24 Authority/groupthink: randomize order, hide identities, report influence Gini.
- B3/Q1-Q14 Overconfidence: weight only by out-of-sample calibration/skill, never self-confidence.
- D1/UQ5 Confirmation: require disconfirming evidence and symmetric counterfactual prompts.
- D3 Organizational learning: freeze forecasts and rubric before outcomes.
- Q28 Conformal prediction: report empirical coverage, not just point estimates.
- UQ2/UQ3 Score spread/uniformity: flag implausible agreement and convergence after exposure.
- UC1-UC5: block governance or learning failures even when the numeric average appears strong.
