"""Deterministic candidate detection for negative parallelism."""

from .detector import CandidateRecord, detect_candidates

__all__ = ["CandidateRecord", "detect_candidates"]
