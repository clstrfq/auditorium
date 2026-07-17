from __future__ import annotations

import hashlib
import math
import re
from typing import Any


TOKENIZER_SPEC = "local-synthetic-tokenizer-v1:regex-word-punctuation:sha256-id"
REFERENCE_SPEC = "local-synthetic-reference-v1:candidate-set-softmax:rejected-bias"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_token_id(token: str) -> int:
    return int(sha256_text(f"{TOKENIZER_SPEC}:{token}")[:8], 16)


def tokenize(text: str) -> list[tuple[int, str]]:
    pieces = re.findall(r"\s+|[\w']+|[^\w\s]", text, flags=re.UNICODE)
    return [(stable_token_id(piece), piece) for piece in pieces]


def tokenizer_sha256() -> str:
    return sha256_text(TOKENIZER_SPEC)


def reference_sha256() -> str:
    return sha256_text(REFERENCE_SPEC)


def _jitter(prefix: str, token_text: str) -> float:
    raw = int(sha256_text(f"{REFERENCE_SPEC}:{prefix}:{token_text}")[:8], 16)
    return (raw / 0xFFFFFFFF - 0.5) * 0.4


def reference_logits(prefix: str, rejected_text: str, chosen_texts: list[str]) -> dict[str, float]:
    result = {rejected_text: 2.4 + _jitter(prefix, rejected_text)}
    for index, token in enumerate(chosen_texts):
        result[token] = 0.4 - 0.05 * index + _jitter(prefix, token)
    return result


def log_softmax(logits: dict[Any, float]) -> dict[Any, float]:
    maximum = max(logits.values())
    log_z = maximum + math.log(sum(math.exp(value - maximum) for value in logits.values()))
    return {key: value - log_z for key, value in logits.items()}


def softmax(logits: dict[Any, float]) -> dict[Any, float]:
    return {key: math.exp(value) for key, value in log_softmax(logits).items()}
