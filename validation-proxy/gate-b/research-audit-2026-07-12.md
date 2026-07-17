# Gate B Research Audit — 2026-07-12

## Decision

The submitted operational specification is **partially accepted with mandatory corrections**. It does not yet authorize corpus collection or model execution.

## Corpus findings

| Proposed source | Finding | Decision |
|---|---|---|
| Crossref abstracts | Crossref metadata is broadly reusable, but Crossref warns that deposited abstracts may remain copyrighted. A `has-license` record is not sufficient because license metadata may identify a text-mining copy rather than the abstract/version of record. | Discovery and DOI reconciliation only; ingest text only after per-item license verification. |
| PubMed abstracts | Abstracts are publisher-supplied and can be copyrighted. PubMed inclusion is not a reuse license. | Discovery only. Prefer PMC OAI/FTP Open Access records with an explicit per-item CC0/CC BY license. |
| ACL Anthology | ACL-hosted materials from 2016 onward are CC BY 4.0; older ACL materials are generally CC BY-NC-SA 3.0. Third-party materials are exceptions. | Accepted academic frame for 2016–2021 ACL-authored records with per-item license and human personal author. |
| Reddit via PRAW | Current Data API terms impose access, privacy, retention/deletion, and termination duties. Bot filters and URL-density rules do not establish authorship or redistribution rights. | Rejected for the frozen redistributable corpus unless a separate Reddit-approved protocol, deletion sync, and legal basis are documented. |
| HuffPost News Category Dataset | The official dataset contains headline, short description, author, URL, category, and date. It does not supply a consistently licensed full article body. Kaggle labels the dataset CC BY 4.0, but that does not establish permission to scrape and redistribute linked HuffPost article bodies. | Accepted only for headline + short-description units if the dataset license is archived and the short description meets the preregistered length requirement. Rejected as a full-article source. |

Pre-2022 publication is a contamination-reduction heuristic, not a guarantee of human authorship. The manifest must use `human_authorship_evidence` and `synthetic_contamination_risk`; it must not store `human_verified=true` solely from date or a personal byline.

### Recommended frozen corpus frame

- D1 Academic, n=100: ACL Anthology 2016–2021 CC BY 4.0 abstracts and/or PMC OA abstracts with explicit CC0/CC BY licenses. Crossref/PubMed may reconcile metadata but cannot confer text rights.
- D2 Forum, n=100: retain the already approved Stack Exchange official dump frame under CC BY-SA. Reddit is a sensitivity/external-validity study only, not the frozen baseline.
- D3 Journalism, n=100: retain individually licensed Global Voices articles. HuffPost headline/description records may be a separate short-form sensitivity panel, not a substitute for article bodies.

## Generation checkpoint research

All seven requested Hugging Face repositories existed when queried on 2026-07-12. Exact repository commits are frozen in `frozen-model-registry.json`. Access is still operationally blocked where license acceptance, weights, compute, tokenizer/runtime validation, or credentials are absent.

The seven checkpoints are not nine configurations and do not share one controlled base. They form a heterogeneous cross-family generation panel. Llama 3 and Llama 3.1 are related releases and Qwen1.5 and Qwen2 are related releases; analyses must model family nesting rather than call all seven independent lineages.

Universal temperature/top-p settings are not semantically identical across tokenizers and model families. Freeze both the requested settings and each model's effective decoding behavior. Use one primary policy (`temperature=0.7`, `top_p=0.9`) and a deterministic seed where honored; record unsupported/ignored fields and do not silently substitute `1.0`.

## Evaluator research

| Evaluator | Verified identity | Dependency finding | Role |
|---|---|---|---|
| GPT-4 Turbo | OpenAI `gpt-4-turbo`; immutable snapshot to be confirmed by a live Models API entitlement check | Proprietary OpenAI lineage | Candidate independent family; endpoint access unresolved |
| ArmoRM | `RLHFlow/ArmoRM-Llama3-8B-v0.1` | Fine-tuned from FsfairX-LLaMA3-RM-v0.1 | Correlated Llama-3 reward cluster |
| Pair preference | `RLHFlow/pair-preference-model-LLaMA3-8B` | Trained from Meta-Llama-3-8B-Instruct | Correlated Llama-3 reward cluster |
| FsfairX BT | `sfairXC/FsfairX-LLaMA3-RM-v0.1` | Base Meta-Llama-3-8B-Instruct; CC BY-NC 4.0 card license | Correlated Llama-3 reward cluster; noncommercial constraint |
| Skywork critic | `Skywork/Skywork-Critic-Llama-3.1-8B` | Base Meta-Llama-3.1-8B-Instruct; training includes OffsetBias data | Correlated Llama cluster and data overlap risk |
| Zephyr beta | `HuggingFaceH4/zephyr-7b-beta` | DPO assistant based on Mistral-7B-v0.1, not a packaged reward model | Mistral methodology probe; implicit-DPO scoring requires base/reference implementation |
| OffsetBias RM | `NCSOFT/Llama-3-OffsetBias-RM-8B` | Derived from/merged with FsfairX and Llama-3-8B-Instruct | Correlated Llama-3 reward cluster, not independent of FsfairX |

These are seven evaluator implementations but only approximately three ancestry clusters: OpenAI, Meta-Llama, and Mistral. The five Llama-derived implementations must not receive five independent-family votes. ArmoRM, FsfairX, and OffsetBias have direct ancestry links; Skywork also reports OffsetBias training data.

## Required evaluator correction

Use the seven implementations for methodology sensitivity, then aggregate hierarchically:

1. Equal weight inside each ancestry cluster.
2. Equal weight across independent ancestry/provider clusters.
3. Estimate residual correlation on a held-out calibration set before computing `n_eff`.
4. Keep the ensemble claim inconclusive unless at least five genuinely distinct ancestry/provider families are acquired and correlation-adjusted `n_eff >= 4`.
5. Add at least two non-Llama families beyond OpenAI and Mistral—preferably one Gemma-family reward/judge and one Qwen-family reward/judge, or independent proprietary providers—with frozen versions and generator-family exclusion.

## Sources

- Crossref REST API and license metadata documentation
- PubMed help/copyright guidance and PMC OA/OAI documentation
- ACL Anthology copyright FAQ
- Reddit Data API Terms effective 2026-07-01
- News Category Dataset paper and official Kaggle record
- Official Hugging Face model cards and repository APIs for every frozen checkpoint/evaluator
- OpenAI GPT-4 Turbo model documentation and deprecation register

