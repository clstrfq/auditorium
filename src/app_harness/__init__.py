"""Reusable adapters for applying the evaluation harness to application data."""

from .adapter import AdaptError, AdaptResult, adapt_corpus

__all__ = ["AdaptError", "AdaptResult", "adapt_corpus"]
