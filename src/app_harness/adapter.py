"""Convert common text corpora to the harness's canonical JSONL contract.

The adapter deliberately performs no inference and has no network dependency.  It
is suitable for use by an application, a Codex skill, or a Claude skill because
identical source bytes and options always produce identical output bytes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


_SUPPORTED_SUFFIXES = {".txt", ".md", ".csv", ".jsonl", ".ndjson"}
_ALIASES: dict[str, frozenset[str]] = {
    "item_id": frozenset({"item_id", "id", "record_id", "document_id", "doc_id", "source_item_id"}),
    "text": frozenset({"text", "content", "body", "document_text", "response", "completion", "output"}),
    "context": frozenset({"context", "source_context", "document_context"}),
    "prompt": frozenset({"prompt", "instruction", "query", "user_prompt"}),
    "model": frozenset({"model", "model_id", "model_name", "generator_model"}),
}
_OPTIONAL_FIELDS = ("context", "prompt", "model")


class AdaptError(ValueError):
    """Raised when source data cannot be safely adapted without guessing."""


@dataclass(frozen=True)
class AdaptResult:
    """Receipt for a successful corpus adaptation.

    ``format`` is the lowercase source suffix without the leading dot.  A
    ``field_map`` value beginning with ``<generated:`` documents a field that
    the adapter derived rather than read from a named source column.
    """

    source_sha256: str
    adapted_sha256: str
    row_count: int
    format: str
    field_map: dict[str, str]

    @property
    def source_format(self) -> str:
        """Descriptive alias for callers that prefer ``source_format``."""

        return self.format


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalise_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _display_fields(fields: Iterable[str]) -> str:
    values = sorted(fields)
    return ", ".join(repr(value) for value in values) if values else "<none>"


def _validate_source_fields(fields: set[str]) -> None:
    if not fields:
        raise AdaptError("source has no fields")
    empty = sorted(field for field in fields if not field.strip())
    if empty:
        raise AdaptError("source contains an empty field name; rename it before adapting")

    by_normalised: dict[str, list[str]] = {}
    for field in fields:
        by_normalised.setdefault(_normalise_field_name(field), []).append(field)
    collisions = [sorted(values) for values in by_normalised.values() if len(values) > 1]
    if collisions:
        rendered = "; ".join(", ".join(repr(value) for value in values) for values in collisions)
        raise AdaptError(
            f"source field names are ambiguous after normalization: {rendered}; "
            "rename the fields so each is unique"
        )


def _resolve_explicit(canonical: str, requested: str, fields: set[str]) -> str:
    if not isinstance(requested, str) or not requested.strip():
        raise AdaptError(f"{canonical}_field must be a non-empty source field name")
    if requested in fields:
        return requested
    normalised = _normalise_field_name(requested)
    matches = [field for field in fields if _normalise_field_name(field) == normalised]
    if len(matches) == 1:
        return matches[0]
    raise AdaptError(
        f"{canonical}_field {requested!r} was not found; available fields: {_display_fields(fields)}"
    )


def _detect_field(
    canonical: str,
    explicit: str | None,
    fields: set[str],
    *,
    required: bool,
) -> str | None:
    if explicit is not None:
        return _resolve_explicit(canonical, explicit, fields)

    matches = sorted(field for field in fields if _normalise_field_name(field) in _ALIASES[canonical])
    if len(matches) > 1:
        raise AdaptError(
            f"ambiguous {canonical} field: {_display_fields(matches)}; "
            f"pass {canonical}_field=... explicitly"
        )
    if len(matches) == 1:
        return matches[0]
    if required:
        raise AdaptError(
            f"could not detect a {canonical} field from {_display_fields(fields)}; "
            f"pass {canonical}_field=... explicitly"
        )
    return None


def _field_map(
    fields: set[str],
    *,
    item_id_field: str | None,
    text_field: str | None,
    context_field: str | None,
    prompt_field: str | None,
    model_field: str | None,
) -> dict[str, str]:
    selected: dict[str, str | None] = {
        "item_id": _detect_field("item_id", item_id_field, fields, required=False),
        "text": _detect_field("text", text_field, fields, required=True),
        "context": _detect_field("context", context_field, fields, required=False),
        "prompt": _detect_field("prompt", prompt_field, fields, required=False),
        "model": _detect_field("model", model_field, fields, required=False),
    }
    used: dict[str, str] = {}
    for canonical, source in selected.items():
        if source is None:
            continue
        if source in used:
            raise AdaptError(
                f"source field {source!r} was assigned to both {used[source]!r} and {canonical!r}; "
                "pass distinct field overrides"
            )
        used[source] = canonical

    result = {canonical: source for canonical, source in selected.items() if source is not None}
    if selected["item_id"] is None:
        result["item_id"] = "<generated:sha256>"
    return result


class _DuplicateJsonKey(ValueError):
    pass


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _read_json_lines(source: Path, limit: int) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    try:
        with source.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                if len(rows) >= limit:
                    break
                try:
                    value = json.loads(line, object_pairs_hook=_object_without_duplicate_keys)
                except (json.JSONDecodeError, _DuplicateJsonKey) as exc:
                    raise AdaptError(f"malformed JSON on line {line_number}: {exc}") from exc
                if not isinstance(value, dict):
                    raise AdaptError(f"malformed JSON on line {line_number}: each row must be an object")
                rows.append((line_number, value))
    except UnicodeDecodeError as exc:
        raise AdaptError(f"{source} is not valid UTF-8: {exc}") from exc
    return rows


def _read_csv(source: Path, limit: int) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames is None:
                raise AdaptError("CSV is empty or has no header row")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise AdaptError("CSV contains duplicate header names; rename them before adapting")
            for row_number, row in enumerate(reader, start=2):
                if len(rows) >= limit:
                    break
                if None in row:
                    raise AdaptError(f"malformed CSV row {row_number}: row has more values than the header")
                missing = [field for field, value in row.items() if value is None]
                if missing:
                    raise AdaptError(
                        f"malformed CSV row {row_number}: missing values for {_display_fields(missing)}"
                    )
                rows.append((row_number, dict(row)))
    except csv.Error as exc:
        raise AdaptError(f"malformed CSV: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise AdaptError(f"{source} is not valid UTF-8: {exc}") from exc
    return rows


def _required_text(row: dict[str, Any], source_field: str, row_number: int) -> str:
    if source_field not in row:
        raise AdaptError(f"row {row_number} is missing text field {source_field!r}")
    value = row[source_field]
    if not isinstance(value, str):
        raise AdaptError(
            f"row {row_number} field {source_field!r} has non-string text "
            f"({type(value).__name__}); convert it to a string before adapting"
        )
    value = value.strip()
    if not value:
        raise AdaptError(f"row {row_number} field {source_field!r} contains empty text")
    return value


def _optional_text(row: dict[str, Any], source_field: str, row_number: int) -> str | None:
    if source_field not in row or row[source_field] is None:
        return None
    value = row[source_field]
    if not isinstance(value, str):
        raise AdaptError(
            f"row {row_number} optional field {source_field!r} must be a string or null, "
            f"not {type(value).__name__}"
        )
    value = value.strip()
    return value or None


def _source_item_id(row: dict[str, Any], source_field: str, row_number: int) -> str:
    if source_field not in row:
        raise AdaptError(f"row {row_number} is missing item ID field {source_field!r}")
    value = row[source_field]
    if isinstance(value, str):
        item_id = value.strip()
    elif isinstance(value, int) and not isinstance(value, bool):
        item_id = str(value)
    else:
        raise AdaptError(
            f"row {row_number} item ID field {source_field!r} must be a string or integer, "
            f"not {type(value).__name__}"
        )
    if not item_id:
        raise AdaptError(f"row {row_number} item ID field {source_field!r} is empty")
    return item_id


def _adapt_rows(
    rows: list[tuple[int, dict[str, Any]]],
    mapping: dict[str, str],
) -> list[dict[str, str]]:
    canonical_rows: list[dict[str, str]] = []
    seen_ids: dict[str, int] = {}
    seen_content: dict[str, int] = {}
    generated_id = mapping["item_id"] == "<generated:sha256>"
    text_source = mapping["text"]

    for row_number, row in rows:
        canonical: dict[str, str] = {"text": _required_text(row, text_source, row_number)}
        for field in _OPTIONAL_FIELDS:
            source_field = mapping.get(field)
            if source_field is None:
                continue
            value = _optional_text(row, source_field, row_number)
            if value is not None:
                canonical[field] = value

        fingerprint = _sha256_bytes(_canonical_json(canonical).encode("utf-8"))
        item_id = fingerprint if generated_id else _source_item_id(row, mapping["item_id"], row_number)
        if item_id in seen_ids:
            raise AdaptError(
                f"duplicate item_id {item_id!r} on row {row_number}; "
                f"first seen on row {seen_ids[item_id]}"
            )
        if fingerprint in seen_content:
            raise AdaptError(
                f"duplicate canonical content on row {row_number}; "
                f"first seen on row {seen_content[fingerprint]}"
            )
        seen_ids[item_id] = row_number
        seen_content[fingerprint] = row_number
        canonical["item_id"] = item_id
        canonical_rows.append(canonical)
    return canonical_rows


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass


def adapt_corpus(
    source: Path,
    output: Path,
    *,
    item_id_field: str | None = None,
    text_field: str | None = None,
    context_field: str | None = None,
    prompt_field: str | None = None,
    model_field: str | None = None,
    limit: int = 500,
) -> AdaptResult:
    """Adapt ``source`` into deterministic canonical JSONL at ``output``.

    TXT and Markdown files become one item.  CSV, JSONL, and NDJSON field names
    are auto-detected only when exactly one conservative alias matches; callers
    can resolve any ambiguity with the keyword field overrides.  At most
    ``limit`` non-blank source rows are adapted, in source order.
    """

    source = Path(source)
    output = Path(output)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise AdaptError("limit must be a positive integer")
    if not source.exists():
        raise AdaptError(f"source does not exist: {source}")
    if not source.is_file():
        raise AdaptError(f"source is not a regular file: {source}")
    if source.resolve() == output.resolve():
        raise AdaptError("source and output must be different paths")

    suffix = source.suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(_SUPPORTED_SUFFIXES))
        raise AdaptError(f"unsupported source format {suffix or '<none>'!r}; supported formats: {supported}")
    try:
        source_bytes = source.read_bytes()
    except OSError as exc:
        raise AdaptError(f"could not read source {source}: {exc}") from exc
    source_sha256 = _sha256_bytes(source_bytes)

    overrides = (item_id_field, text_field, context_field, prompt_field, model_field)
    if suffix in {".txt", ".md"}:
        if any(value is not None for value in overrides):
            raise AdaptError("field overrides are only valid for CSV, JSONL, and NDJSON sources")
        try:
            text = source_bytes.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            raise AdaptError(f"{source} is not valid UTF-8: {exc}") from exc
        if not text:
            raise AdaptError("source contains no non-whitespace text")
        content = {"text": text}
        content["item_id"] = _sha256_bytes(_canonical_json(content).encode("utf-8"))
        canonical_rows = [content]
        mapping = {"item_id": "<generated:sha256>", "text": "<document>"}
    else:
        rows = _read_csv(source, limit) if suffix == ".csv" else _read_json_lines(source, limit)
        if not rows:
            raise AdaptError("source contains no data rows")
        fields = {field for _, row in rows for field in row}
        _validate_source_fields(fields)
        mapping = _field_map(
            fields,
            item_id_field=item_id_field,
            text_field=text_field,
            context_field=context_field,
            prompt_field=prompt_field,
            model_field=model_field,
        )
        canonical_rows = _adapt_rows(rows, mapping)

    payload = "".join(_canonical_json(row) + "\n" for row in canonical_rows).encode("utf-8")
    try:
        _atomic_write(output, payload)
    except OSError as exc:
        raise AdaptError(f"could not write adapted corpus {output}: {exc}") from exc
    return AdaptResult(
        source_sha256=source_sha256,
        adapted_sha256=_sha256_bytes(payload),
        row_count=len(canonical_rows),
        format=suffix[1:],
        field_map=dict(sorted(mapping.items())),
    )
