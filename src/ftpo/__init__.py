"""Preparation-only contracts and leakage-safe splitting for FTPO datasets."""

from .schema import ValidationError, validate_example
from .split import SplitConfig, split_examples

__all__ = ["SplitConfig", "ValidationError", "split_examples", "validate_example"]
