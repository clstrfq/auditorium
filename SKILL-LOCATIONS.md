# Skill Locations

<!-- artifact-id: skill-locations | schema: v1 -->

Where every one of the eight skills lives, in every form, across this project.
The consolidated, share-ready set is **`The Auditorium/`** — named for what the
eight skills have in common: every one of them audits, verifies, gates, or
receipts. The live, lintable sources stay in the main project tree.

## The eight skills

`apply-app-harness` · `slop-pattern-auditor` · `qa-companion` · `agent-shape-selector` ·
`agent-memory-architect` · `handoff-ticket-designer` · `model-routing-economist` ·
`trust-verification-architect`

## Consolidated set (share this folder)

Everything a user needs, for both hosts, lives in `The Auditorium/`:

| Path | Contents | Use it for |
|---|---|---|
| `The Auditorium/claude-skill-packages/` | Eight installable `.skill` archives with the Claude banner | Claude / Claude Code / Cowork — install directly (Save skill), or unzip into `~/.claude/skills/` or `.claude/skills/`; invoke as `/<name>` |
| `The Auditorium/codex-skill-packages/` | The same eight as Codex-banner `.skill` archives | Codex — unzip into `~/.codex/skills/` or `.codex/skills/`; invoke as `$<name>` |
| `The Auditorium/skills/` | The eight unpacked `SKILL.md` source directories (Claude-banner text; `apply-app-harness` carries its host-neutral portable banner by design) | Reading, reviewing, or referencing from `AGENTS.md` in any other agent host |
| `The Auditorium/README.md` | Full index: what each skill produces, when to reach for it, the five design guarantees, and the cross-skill hooks table | Orientation |

This folder is a verified snapshot: every file byte-matches the main-tree original
it was copied from, and its `skills/` tree lints 8/8 against the five guarantees.
It contains no scripts — regenerate in the main tree, then re-copy.

## Live sources (edit and regenerate here)

| Path | Contents | Role |
|---|---|---|
| `skills/<name>/SKILL.md` | Canonical skill text, all eight | Source of truth; what `scripts/lint_skills.py skills` gates |
| `chatgpt-skill-packages/*.skill` | Eight Codex-banner source archives | Input to the Claude generator |
| `claude-skill-packages/*.skill` | Eight generated Claude packages | Output of `scripts/generate_claude_skills.py` |
| `.claude/skills/apply-app-harness/`, `.codex/skills/apply-app-harness/` | Installed copies of the harness skill on this machine's two surfaces | What `./harness install` maintains; byte-identical to the canonical skill |
| `evals/adversarial/slop-pattern-auditor/` | Adversarial corpus, expected findings, and the Haiku/Sonnet/Opus eval report | Evidence behind slop-pattern-auditor |

For the six skills that flow through the generator, the pipeline is:
`chatgpt-skill-packages/<name>.skill` → `scripts/generate_claude_skills.py` →
`skills/<name>/SKILL.md` + `claude-skill-packages/<name>.skill` (idempotent,
self-linting). `apply-app-harness` is maintained directly in `skills/` and packaged
byte-identically for both hosts. After any regeneration, refresh the consolidated
folder by copying the changed files and re-running
`python3 scripts/lint_skills.py "The Auditorium/skills"`.

## Change log
- v1 (2026-07-19): initial map; eight skills across consolidated and live locations
- v2 (2026-07-19): consolidated folder renamed "Negative Parallelism Skills" → "The Auditorium"; naming policy recorded in the folder README
