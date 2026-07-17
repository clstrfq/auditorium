# M4 Brief: Review Console and Controls

## Purpose and FR ownership

Provide the realistic human decision surface and safe operational controls. Owns FR7, user-facing FR11, and external-inference approvals under FR12.

## Interface contract

**Input:** manifest, normalized source, candidates, classifications, rewrites, verifications, current control state.  
**Output:** append-only `ReviewEvent` and `ControlEvent` records.  
**Failure:** stale artifact hash, conflicting reviewer event, missing evidence, unauthorized approval.  
**Permission:** named local reviewer may decide, pause, resume, cancel, export; cannot mutate evidence or publish.

```text
load evidence by artifact hash
show source context, label, rationale, candidates, check deltas
on action: verify hashes are current
append accept/edit/reject/defer or approval event
on control: append pause/resume/cancel/export event
```

## Alternatives

- A: Local web console with server-rendered queue and keyboard actions.
- B: Static Markdown/CSV review packet plus CLI event importer. Faster but weak for timing and control tests.

## Verification

Stale-review rejection; keyboard-only walkthrough; uncertain and failed items cannot disappear; pause finishes current atomic item; edited rewrite retains provenance; no publication control exists.
