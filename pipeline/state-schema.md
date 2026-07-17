# Pipeline State Schema

## Version 1.2

`pipeline/state.json` is durable cycle memory. The manager replaces it atomically after a verified transition.

Required top-level fields are `schema_version`, `project`, `mode`, `last_cycle_id`, `input_watermarks`, `budget`, `items`, `paused`, `pause_reason`, `build`, and `updated_at`.

Allowed modes:

- `ready`: inputs exist and no build is active.
- `running`: a transient local engineering build owns the lock.
- `build_complete`: the engineering receipt and artifacts verify.
- `failed`: the most recent build failed and the prior verified artifacts, if any, remain authoritative.

Build invariants:

- `build_complete` requires `pipeline/BUILD_COMPLETE`, no `pipeline/RUNNING`, `paused=false`, and a passing receipt pointer/hash.
- The former `pipeline/PAUSED` and `pipeline/PREP_ONLY` sentinels must not exist.
- `done` items require non-null output pointers and successful gate receipts.
- Train, validation, and holdout registered-key overlap is zero.
- Generated datasets declare origin, tier, reference/tokenizer hashes, and forbidden claim scope.
- B0-B3 run against the same frozen inputs and seed list.
- Nonfinite loss or update cannot produce a promoted checkpoint.
- External effects are recorded independently; zero values mean none occurred, not that an external run was simulated.

## Changelog

- 1.2 - Added `build_complete`, generated-data execution, typed evidence, and removed legacy sentinel modes.
- 1.1 - Added the former preparation and external-execution modes.
- 1.0 - Initial durable state contract.
