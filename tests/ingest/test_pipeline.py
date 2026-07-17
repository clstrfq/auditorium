import json
from pathlib import Path

import pytest

from src.contracts import IngestConfig
from src.ingest import ForbiddenDestinationError, ingest_file
from src.ingest import pipeline
from src.state import RunStore


def config(**changes):
    values = {
        "field_map": {"item_id": "id", "text": "body", "context": "context"},
        "ruleset_version": "rules-1",
        "rubric_version": "rubric-1",
        "threshold_version": "thresholds-1",
    }
    values.update(changes)
    return IngestConfig(**values)


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("corpus.csv", "id,body,context\na,First text,nearby\nb,Second text,other\n"),
        ("corpus.jsonl", '{"id":"a","body":"First text","context":"nearby"}\n'
                         '{"id":"b","body":"Second text","context":"other"}\n'),
    ],
)
def test_golden_imports_and_identical_rerun(tmp_path, name, content):
    source = tmp_path / name
    source.write_text(content, encoding="utf-8")

    first = ingest_file(source, config(), tmp_path / "project")
    second = ingest_file(source, config(), tmp_path / "project")

    assert first.receipt["status"] == "successful"
    assert second.deduplicated is True
    assert second.receipt == first.receipt
    run_dir = tmp_path / "project" / "runs" / first.run_id
    items = read_jsonl(run_dir / "normalized.jsonl")
    assert [item["item_id"] for item in items] == ["a", "b"]
    assert all(item["schema_version"] == "1.0.0" for item in items)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["normalized_count"] == 2
    assert manifest["field_map"]["text"] == "body"


def test_invalid_and_duplicate_rows_are_quarantined(tmp_path):
    source = tmp_path / "corpus.jsonl"
    source.write_text('{"id":"a","body":"ok"}\n{"id":"a","body":"again"}\nnot-json\n'
                      '{"id":"b","body":3}\n', encoding="utf-8")

    result = ingest_file(source, config(), tmp_path / "project")
    run_dir = tmp_path / "project" / "runs" / result.run_id

    assert len(read_jsonl(run_dir / "normalized.jsonl")) == 1
    quarantined = read_jsonl(run_dir / "quarantine.jsonl")
    assert len(quarantined) == 3
    assert quarantined[0]["reason"] == "duplicate_item_id"
    assert all(row["status"] == "quarantined" for row in quarantined)


def test_forbidden_destination_blocks_before_source_read(monkeypatch, tmp_path):
    source = tmp_path / "secret.jsonl"
    source.write_text('{"id":"a","body":"secret"}\n', encoding="utf-8")
    monkeypatch.setattr(pipeline, "_hash_file", lambda _path: pytest.fail("source was read"))

    with pytest.raises(ForbiddenDestinationError, match="https://provider.example"):
        ingest_file(source, config(model_destinations=("https://provider.example",)), tmp_path / "project")


def test_interrupted_run_resumes_without_duplicate_records(monkeypatch, tmp_path):
    source = tmp_path / "corpus.csv"
    source.write_text("id,body\na,one\nb,two\nc,three\n", encoding="utf-8")
    original_control = RunStore.control
    calls = 0

    def pause_after_one(self, run_id):
        nonlocal calls
        calls += 1
        return "paused" if calls == 2 else original_control(self, run_id)

    monkeypatch.setattr(RunStore, "control", pause_after_one)
    paused = ingest_file(source, config(), tmp_path / "project")
    assert paused.receipt["status"] == "paused"
    monkeypatch.setattr(RunStore, "control", original_control)
    RunStore(tmp_path / "project").set_control(paused.run_id, "running")

    completed = ingest_file(source, config(), tmp_path / "project")
    items = read_jsonl(tmp_path / "project" / "runs" / completed.run_id / "normalized.jsonl")
    assert [item["item_id"] for item in items] == ["a", "b", "c"]
    assert len({item["item_id"] for item in items}) == 3


def test_config_requires_explicit_stable_id_mapping():
    with pytest.raises(ValueError, match="item_id and text"):
        config(field_map={"text": "body"})
