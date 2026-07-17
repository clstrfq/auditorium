from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Mapping, Sequence

from .models import ControlEvent, ReviewEvent
from .store import EventLedger, StaleArtifactError, artifact_hash


@dataclass(frozen=True)
class ReviewBundle:
    item: Any
    candidate: Any
    classification: Any
    rewrites: Sequence[Any]
    verifications: Sequence[Any]

    @property
    def hashes(self) -> dict[str, str]:
        values = {"item": self.item, "candidate": self.candidate,
                  "classification": self.classification}
        values.update({f"rewrite:{r.rewrite_id}": r for r in self.rewrites})
        values.update({f"verification:{v.rewrite_id}": v for v in self.verifications})
        return {key: artifact_hash(value) for key, value in values.items()}


class ReviewConsole:
    def __init__(self, ledger: EventLedger, bundles: Mapping[str, ReviewBundle]) -> None:
        self.ledger = ledger
        self.bundles = dict(bundles)

    def _current(self, candidate_id: str, displayed_hashes: Mapping[str, str]) -> ReviewBundle:
        bundle = self.bundles[candidate_id]
        if dict(displayed_hashes) != bundle.hashes:
            raise StaleArtifactError("displayed evidence is stale; reload before submitting")
        return bundle

    def decide(self, candidate_id: str, displayed_hashes: Mapping[str, str], reviewer_id: str,
               action: str, selected_rewrite_id: str | None = None,
               edited_text: str | None = None, reason: str = "") -> ReviewEvent:
        bundle = self._current(candidate_id, displayed_hashes)
        if selected_rewrite_id and selected_rewrite_id not in {r.rewrite_id for r in bundle.rewrites}:
            raise ValueError("selected rewrite is not part of the displayed evidence")
        return self.ledger.append_review(
            run_id=bundle.item.run_id, input_hash=bundle.item.input_hash,
            reviewer_id=reviewer_id, action=action, candidate_id=candidate_id,
            artifact_hashes=bundle.hashes, selected_rewrite_id=selected_rewrite_id,
            edited_text=edited_text, reason=reason)

    def control(self, candidate_id: str, displayed_hashes: Mapping[str, str], reviewer_id: str,
                action: str, reason: str = "") -> ControlEvent:
        bundle = self._current(candidate_id, displayed_hashes)
        return self.ledger.append_control(
            run_id=bundle.item.run_id, input_hash=bundle.item.input_hash,
            reviewer_id=reviewer_id, action=action, artifact_hashes=bundle.hashes, reason=reason)

    def render(self, candidate_id: str) -> str:
        b = self.bundles[candidate_id]
        failed = [v for v in b.verifications if v.decision != "verified"]
        options = "".join(
            f'<article><h3>Rewrite {r.alternative_index}</h3><p>{escape(r.rewrite_text)}</p>'
            f'<p>Provenance: {escape(r.generator_identity)} · {escape(r.rewrite_id)}</p></article>'
            for r in b.rewrites)
        blocks = "".join(
            f'<li>{escape(v.rewrite_id)}: {escape(v.decision)} — '
            f'{escape(", ".join(v.blocking_reasons) or "all checks passed")}</li>'
            for v in b.verifications)
        warning = '<p role="alert">Blocked or unresolved evidence remains visible.</p>' if (
            b.classification.label == "uncertain" or failed) else ""
        hidden = "".join(f'<input type="hidden" name="hash:{escape(key)}" value="{value}">'
                         for key, value in b.hashes.items())
        rewrite_choices = "".join(
            f'<option value="{escape(r.rewrite_id)}">Rewrite {r.alternative_index}</option>'
            for r in b.rewrites)
        return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Review {escape(candidate_id)}</title></head><body><main><h1>Evidence review</h1>{warning}
<section aria-labelledby="source"><h2 id="source">Source context</h2><p>{escape(b.candidate.context_window)}</p>
<p>Rule: {escape(b.candidate.matched_rule)} · Span: {b.candidate.span_start}–{b.candidate.span_end}</p></section>
<section aria-labelledby="classification"><h2 id="classification">Classification</h2>
<p>{escape(b.classification.label)} ({b.classification.confidence:.2f}): {escape(b.classification.rationale)}</p></section>
<section aria-labelledby="rewrites"><h2 id="rewrites">Rewrite candidates</h2>{options}</section>
<section aria-labelledby="verification"><h2 id="verification">Verification and metric deltas</h2><ul>{blocks}</ul></section>
<form method="post">{hidden}<label>Reviewer <input name="reviewer_id" required></label>
<label>Reason <textarea name="reason"></textarea></label>
<label>Selected rewrite <select name="selected_rewrite_id"><option value="">None</option>{rewrite_choices}</select></label>
<label>Edited text <textarea name="edited_text"></textarea></label>
<fieldset><legend>Decision</legend><button name="action" value="accept">Accept</button>
<button name="action" value="edit">Edit</button><button name="action" value="reject">Reject</button>
<button name="action" value="defer">Defer</button></fieldset>
<fieldset><legend>Run controls</legend><button name="action" value="pause">Pause after current item</button>
<button name="action" value="resume">Resume</button><button name="action" value="cancel">Cancel safely</button>
<button name="action" value="export">Export evidence</button>
<button name="action" value="approve_external_inference">Approve external inference</button>
<button name="action" value="approve_release">Approve release</button></fieldset>
</form></main></body></html>'''
