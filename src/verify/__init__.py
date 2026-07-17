"""Independent, fail-closed verification for M3 rewrite proposals."""

from .verifier import VerificationPolicy, VerificationRecord, verify_rewrite, verify_rewrites

__all__ = ["VerificationPolicy", "VerificationRecord", "verify_rewrite", "verify_rewrites"]
