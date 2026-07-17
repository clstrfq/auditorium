# Gate B Clearance Assessment — Proposed Execution Architecture

## Clearance decision

**NOT CLEARED. `pipeline/PAUSED` remains authoritative.**

The proposal improves the within-base causal panel through OLMo 3 but does not resolve corpus licensing, human-authorship verification, executable credentials/compute, or evaluator-family independence.

## Corpus assessment

| Candidate | Finding | Gate status |
|---|---|---|
| arXiv abstracts | arXiv metadata may be reused under its metadata terms, but “January 2018 through November 2022” is not strictly pre-2022. A date/byline cannot guarantee absence of AI assistance, and arXiv is not uniformly peer reviewed. Freeze submission version and license evidence per record. | Conditional candidate; redefine cutoff as `<= 2021-12-31` or label the 2022 records a contamination sensitivity panel. |
| ArgRewrite V.2 | Documented student revision corpus about self-driving cars, but public metadata located in this audit did not establish a sufficiently explicit text-redistribution license and consent scope for this use. It is also narrow-domain student argumentation rather than academic abstracts. | Blocked pending license, data-use, and consent documentation. |
| Arctic Shift / Pushshift Reddit | Archive/repackaging does not grant rights in user content. Current Pushshift access is limited to approved moderation use; archived deleted content creates deletion and privacy risks. | Rejected from frozen redistributable baseline absent Reddit authorization, legal/IRB protocol, and deletion synchronization. |
| Essays personality corpus | The original Pennebaker/King corpus is described as about 2,344 student essays, not reliably 2,348. No authoritative redistributable license was verified. It contains sensitive personality-linked student writing. Do not confuse it with the explicitly synthetic 2024 Big5PersonalityEssays dataset. | Blocked pending authoritative license, consent, privacy, and exact-version evidence. |
| Patch News | Patch terms grant Patch rights from contributors; they do not grant this project a reusable corpus license. No authoritative licensed Patch full-text dataset was verified. | Rejected pending an explicit dataset/content license. |
| HuffPost News Category | Contains headline and short description metadata, not a dependable full article body. Dataset-level CC BY labeling does not license independently scraped article bodies. | Sensitivity panel only; not full journalism corpus. |

The previously approved frames therefore remain the lowest-risk path: individually licensed ACL/PMC OA academic abstracts, Stack Exchange official dump prose, and individually licensed Global Voices journalism.

## Model checkpoint assessment

### OLMo 3 — accepted conditional panel

Ai2 exposes Apache-2.0 OLMo 3 7B base, Think-SFT, Think-DPO, final Think, Instruct-SFT, Instruct-DPO, final Instruct, and experimental RL-Zero checkpoints. This is the strongest available matched-stage panel.

Before execution, freeze for every arm:

- exact Hugging Face repository and commit SHA;
- tokenizer/config/weight hashes;
- Transformers and CUDA container digest;
- chat template and stop rules;
- effective sampling parameters and seeds;
- prompt hashes and output limits;
- hardware/quantization mode.

“Perfect control” is disallowed: training datasets, objectives, and stage transitions differ by design, and the analysis must retain stage-by-lineage interactions.

### Frontier baselines — candidates, not frozen endpoints

- Claude Opus 4.7 exists as `claude-opus-4-7`, but Opus 4.8 is now Anthropic’s newer generally available model. Opus 4.7 rejects non-default `temperature`, `top_p`, and `top_k`, so the universal decoding policy cannot be applied to it.
- Gemini 3.1 Pro exists as `gemini-3.1-pro-preview`. It is a preview model with no immutable public checkpoint and can change or be retired; store the API-returned model version and repeat sentinel prompts each run.
- DeepSeek V3.2 open weights exist, but the DeepSeek API aliases `deepseek-chat` and `deepseek-reasoner` now point to DeepSeek V4 Flash and are scheduled for discontinuation on 2026-07-24. Reproducible V3.2 requires freezing and self-hosting the open-weight checkpoint or obtaining a provider-specific immutable deployment.

No endpoint is executable until credentials, account entitlement, budget, data-retention terms, and a successful zero-content connectivity receipt are recorded.

## Evaluator assessment

The proposed five are five methodologies but not five independent families:

- ArmoRM is fine-tuned from FsfairX.
- FsfairX, Pair Preference, ArmoRM, and Skywork Critic are Meta-Llama descendants.
- Zephyr adds one Mistral ancestry but is an assistant; implicit DPO reward requires the frozen Mistral base/reference and a validated scoring implementation.
- OffsetBias is derived from/merged with FsfairX and therefore cannot be its independent backup.
- GPT-4 Turbo adds one OpenAI family but is a legacy model and requires a live entitlement/snapshot check.

For methodology analysis, retain all proposed implementations with nested weights. For an ensemble-independence claim, add enough Gemma/Qwen/other-provider families to reach five ancestry/provider clusters and correlation-adjusted `n_eff >= 4`.

## Exact events that clear the blockers

Corpus clearance requires:

1. A 300-row manifest validates against the frozen schema.
2. Every row carries a direct source URI, version/date, personal-author evidence, license URI/evidence, acquisition method, and content hash.
3. Rights/privacy review has no unresolved record.
4. The cutoff is internally consistent and never called a guarantee of human authorship.

Model clearance requires:

1. Local weight paths or API credentials/account entitlements exist.
2. Exact revisions/deployment identifiers and runtime hashes are recorded.
3. A no-sensitive-content connectivity/load test passes for every arm and evaluator.
4. Estimated spend is approved and bounded.
5. At least five genuinely distinct evaluator ancestry/provider clusters pass the dependency audit.

Until both receipts exist, no readiness confirmation may be issued.

