from .test_m2 import fixtures
from src.classify import classify_candidates
from src.detect import detect_candidates


CASES = [
    ("It is not a tool, but a revolution.", "harmful"),
    ("This is not red, but blue; the difference is material.", "legitimate"),
    ("Choose clarity rather than ornamentation in this unusually elaborate sentence.", "uncertain"),
    ("Plain declarative prose.", None),
]


def test_frozen_eval_metrics():
    expected_candidates = sum(label is not None for _, label in CASES)
    detected = correct = confident_correct = 0
    for text, expected in CASES:
        manifest, item = fixtures(text)
        candidates = detect_candidates(manifest, item)
        detected += bool(candidates)
        if expected:
            result = classify_candidates(manifest, item, candidates)[0]
            correct += result.label == expected
            confident_correct += (result.label == expected) if result.confidence >= .7 else (result.label == "uncertain")
    precision = expected_candidates / detected
    recall = detected / expected_candidates
    calibration = confident_correct / expected_candidates
    assert precision == 1.0 and recall == 1.0 and calibration == 1.0 and correct == expected_candidates
