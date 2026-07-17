# M2 Brief: Detect and Classify

## Purpose and FR ownership

Find high-recall candidate spans and distinguish harmful, legitimate, and uncertain uses with evidence. Owns FR3 and FR4.

## Interface contract

**Input:** `RunManifest`, `NormalizedItem[]`, versioned ruleset and rubric.  
**Output:** `CandidateRecord[]`, `ClassificationRecord[]`.  
**Failure:** offset mismatch, unsupported language, model timeout/malformed result, confidence below policy.  
**Permission:** read M1 artifacts; append M2 artifacts; optional approved/redacted model call only.

```text
for item in normalized_items:
  treat text as quoted data
  candidates = deterministic_rules(item.text)
  for candidate in candidates:
    context = bounded_window(candidate)
    label = fixture_or_approved_classifier(context, rubric)
    if unsupported or low confidence: label = uncertain
    append candidate and classification
```

## Alternatives

- A: Regex/rule detector plus rubric-bound model classifier with abstention.
- B: Fully deterministic rules and reviewer labeling. Lower contextual automation; strong fallback if external inference is disallowed.

## Verification

Span-offset property tests; prompt-injection fixtures; legitimate-contrast set; unsupported language routes to uncertain; frozen adjudicated set calculates precision, recall, confusion matrix, and calibration.
