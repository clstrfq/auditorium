# Day 3: Decide

## Decider criteria

Each alternative is scored 1-5. Hypothesis fit rewards contextual judgment plus auditability; cost rewards the smaller build; risk rewards fewer unvalidated dependencies.

| Module | Option | Hypothesis fit | Cost | Risk | Total | Decision |
|---|---|---:|---:|---:|---:|---|
| M1 | Python CLI + atomic files | 5 | 5 | 4 | 14 | **Choose** |
| M1 | SQLite import platform | 4 | 3 | 3 | 10 | Reject: premature persistence complexity |
| M2 | Rules + classifier/abstention | 5 | 4 | 3 | 12 | **Choose**, with fixture mode |
| M2 | Rules + manual labels | 3 | 5 | 5 | 13 | Retain as fallback; does not test assisted contextual judgment |
| M3 | Multiple generation + layered checks | 5 | 3 | 3 | 11 | **Choose**, with fixture mode and hard blocks |
| M3 | Template editor | 3 | 5 | 4 | 12 | Fallback if fidelity gate fails |
| M4 | Local web console | 5 | 3 | 4 | 12 | **Choose** |
| M4 | Markdown/CSV + CLI importer | 3 | 5 | 4 | 12 | Reject: cannot test workflow speed/control credibly |
| M5 | JSON/Markdown aggregation + receipt | 5 | 5 | 5 | 15 | **Choose** |
| M5 | Analytics database/dashboard | 4 | 2 | 3 | 9 | Reject: not needed for hypothesis |

## Frozen implementation decisions

- M1: Python CLI, strict schemas, atomic files, append-only JSONL, SHA-256 identity.
- M2: deterministic candidate rules followed by a rubric classifier that can abstain; deterministic fixture adapter is the default prototype backend.
- M3: two or more rewrite candidates; exact protected-field checks plus independently configured semantic verification; fixture adapter permits offline testing.
- M4: local web console; no authentication service, publication action, or production design system in prototype.
- M5: deterministic Python aggregation to JSON and Markdown with content-hash receipts.

## Resolved conflicts

1. **Who owns stage state?** M1 owns checkpoints and consumes M4 control events; modules own only their append-only result artifacts.
2. **Can M3 process uncertain items?** Only after an explicit M4 reviewer-selection event; otherwise uncertain items remain queued.
3. **Who accepts rewrites?** Only M4 records human decisions. M3 verification can block but never accept.
4. **What makes runs comparable?** M5 requires the same normalized item IDs and compatible metric-policy versions; other comparisons are descriptive and visibly non-paired.
5. **What creates replay cases?** M5 proposes; a human approval event promotes them in a later run/config revision.
6. **External model behavior?** M1 policy must authorize the destination before M2/M3 adapters can send redacted context.

**Gate result: PASS.** One implementation is selected for every module; all producer, consumer, authority, and comparison conflicts are resolved.
