"""Counterfactual rewrite generation with fail-closed eligibility."""

from .generator import (
    FixtureGenerator,
    ReviewerSelectionEvent,
    RewriteRecord,
    generate_rewrites,
)

__all__ = ["FixtureGenerator", "ReviewerSelectionEvent", "RewriteRecord", "generate_rewrites"]
