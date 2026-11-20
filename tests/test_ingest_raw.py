"""Raw-zone ingestion (issue #12): files land byte for byte under the convention's layout,
each load writes a manifest, and a rerun writes no duplicates. A local folder stands in
for the bucket, so these tests need no cloud access."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

import pytest

from data.ingestion.ingest_raw import LocalStore, count_csv_rows, ingest, main

DAY1 = datetime(2026, 11, 19, 15, 30, tzinfo=UTC)
LAYOUT = re.compile(
    r"^claims_batch/source=synthetic/ingest_date=\d{4}-\d{2}-\d{2}/[a-z0-9_]+_\d{8}_\d{3}\.csv$")
MANIFEST_KEYS = {"manifest_version", "load_id", "ingest_time", "domain", "source",
                 "source_type", "license_note", "dry_run", "files", "skipped",
                 "manifest_object"}
FILE_KEYS = {"object", "original_name", "dataset", "size_bytes", "sha256", "row_count"}


@pytest.fixture
def src(tmp_path):
    d = tmp_path / "in"
    d.mkdir()
    (d / "claims.csv").write_text("claim_id,note\nC1,a\nC2,\"two\nlines\"\nC3,c\n", "utf-8")
    (d / "vendors.csv").write_text("vendor_id\nV1\n", "utf-8")
    (d / "readme.txt").write_text("not a csv", "utf-8")
    (d / "truth").mkdir()  # a subfolder (like planted truth) must never be picked up
    (d / "truth" / "rings.csv").write_text("ring_id\nR1\n", "utf-8")
    return d


@pytest.fixture
def store(tmp_path):
    return LocalStore(tmp_path / "bucket")


def data_objects(store):
    return {k for k in store.list_objects("") if not k.startswith("_manifests/")}


def manifests(store):
    return [k for k in store.list_objects("_manifests/")]


def test_first_load_follows_layout_and_keeps_bytes(src, store):
    m = ingest(src, store, now=DAY1)
    objs = sorted(data_objects(store))
    assert objs == [
        "claims_batch/source=synthetic/ingest_date=2026-11-19/claims_20261119_001.csv",
        "claims_batch/source=synthetic/ingest_date=2026-11-19/vendors_20261119_001.csv",
    ]
    assert all(LAYOUT.match(o) for o in objs)
    for f in m["files"]:
        stored = (store.root / f["object"]).read_bytes()
        assert stored == (src / f["original_name"]).read_bytes()
        assert hashlib.sha256(stored).hexdigest() == f["sha256"]


def test_manifest_has_every_required_field(src, store):
    m = ingest(src, store, now=DAY1, load_id="L1")
    assert set(m) == MANIFEST_KEYS
    assert m["manifest_object"] == "_manifests/source=synthetic/ingest_date=2026-11-19/load_L1.json"
    assert json.loads((store.root / m["manifest_object"]).read_text("utf-8")) == m
    assert m["ingest_time"] == "2026-11-19T15:30:00Z"
    assert m["source_type"] == "synthetic" and m["license_note"]
    by_name = {f["original_name"]: f for f in m["files"]}
    assert all(set(f) == FILE_KEYS for f in m["files"])
    assert by_name["claims.csv"]["row_count"] == 3  # quoted line break stays in one row
    assert by_name["vendors.csv"]["row_count"] == 1
    assert by_name["claims.csv"]["size_bytes"] == (src / "claims.csv").stat().st_size


def test_rerun_same_day_writes_nothing(src, store):
    ingest(src, store, now=DAY1)
    before = store.list_objects("")
    m = ingest(src, store, now=DAY1 + timedelta(minutes=5))
    assert m["files"] == [] and len(m["skipped"]) == 2
    assert m["manifest_object"] is None
    assert store.list_objects("") == before


def test_rerun_next_day_is_still_not_a_duplicate(src, store):
    ingest(src, store, now=DAY1)
    m = ingest(src, store, now=DAY1 + timedelta(days=1))
    assert m["files"] == []
    assert len(data_objects(store)) == 2 and len(manifests(store)) == 1


def test_changed_file_is_a_redelivery_with_next_sequence(src, store):
    first = ingest(src, store, now=DAY1)
    old = next(f["object"] for f in first["files"] if f["dataset"] == "claims")
    old_bytes = (store.root / old).read_bytes()
    (src / "claims.csv").write_text("claim_id,note\nC1,a\nC9,new\n", "utf-8")
    m = ingest(src, store, now=DAY1 + timedelta(hours=1))
    assert [f["object"].rsplit("/", 1)[-1] for f in m["files"]] == ["claims_20261119_002.csv"]
    assert [s["original_name"] for s in m["skipped"]] == ["vendors.csv"]
    assert (store.root / old).read_bytes() == old_bytes  # write once: old file untouched
    assert len(manifests(store)) == 2


def test_redelivery_on_a_new_day_starts_at_sequence_one(src, store):
    ingest(src, store, now=DAY1)
    (src / "claims.csv").write_text("claim_id,note\nC7,x\n", "utf-8")
    m = ingest(src, store, now=DAY1 + timedelta(days=1))
    assert m["files"][0]["object"].endswith("ingest_date=2026-11-20/claims_20261120_001.csv")


def test_dry_run_writes_nothing(src, store):
    m = ingest(src, store, now=DAY1, dry_run=True)
    assert len(m["files"]) == 2 and m["dry_run"] is True
    assert m["manifest_object"] is None
    assert store.list_objects("") == {}


def test_store_refuses_to_overwrite(store):
    store.create("a/b.csv", b"one", {}, "text/csv")
    with pytest.raises(FileExistsError):
        store.create("a/b.csv", b"two", {}, "text/csv")
    assert (store.root / "a/b.csv").read_bytes() == b"one"


def test_dataset_name_is_lowercase_without_spaces(tmp_path, store):
    d = tmp_path / "odd"
    d.mkdir()
    (d / "Claims Data.csv").write_text("x\n1\n", "utf-8")
    m = ingest(d, store, now=DAY1)
    assert m["files"][0]["object"].endswith("/claims_data_20261119_001.csv")
    assert m["files"][0]["original_name"] == "Claims Data.csv"


@pytest.mark.parametrize("kwargs, message", [
    ({"source": "public_kaggle_claims"}, "license note"),
    ({"source": "public_x", "license_note": "  "}, "license note"),
    ({"source": "Real_Insurer"}, "source must be"),
    ({"domain": "documents"}, "unsupported domain"),
])
def test_bad_arguments_are_refused(src, store, kwargs, message):
    with pytest.raises(ValueError, match=message):
        ingest(src, store, now=DAY1, **kwargs)
    assert store.list_objects("") == {}


def test_public_source_with_license_note_is_recorded(src, store):
    m = ingest(src, store, now=DAY1, source="public_x", license_note="CC BY 4.0 (register S99)")
    assert m["source_type"] == "public" and m["license_note"] == "CC BY 4.0 (register S99)"
    assert m["files"][0]["object"].startswith("claims_batch/source=public_x/")


def test_empty_folder_is_refused(tmp_path, store):
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="no .csv files"):
        ingest(tmp_path / "empty", store, now=DAY1)


def test_row_count_of_header_only_file_is_zero(tmp_path):
    p = tmp_path / "h.csv"
    p.write_text("a,b\n", "utf-8")
    assert count_csv_rows(p) == 0


def test_command_line_with_local_root(src, tmp_path, capsys):
    root = tmp_path / "cli_bucket"
    first = main(["--in", str(src), "--local-root", str(root)])
    second = main(["--in", str(src), "--local-root", str(root)])
    out = capsys.readouterr().out
    assert len(first["files"]) == 2 and second["files"] == []
    assert "skipped claims.csv" in out


def test_command_line_needs_a_target(src, monkeypatch):
    monkeypatch.delenv("CLAIMGUARD_RAW_BUCKET", raising=False)
    with pytest.raises(SystemExit):
        main(["--in", str(src)])
