"""File-level contract checks (issue #11): bad files are rejected whole, good files pass."""

from pathlib import Path

import pytest

from data.contracts.check_file import check_file
from data.generators.claims_world import COLUMNS, generate, write_csv
from tests.test_claims_world import SMALL

FIXTURES = Path("tests/fixtures/contract")


@pytest.mark.parametrize("name, reason", [
    ("bad_missing_column.csv", "missing column: phone"),
    ("bad_extra_column.csv", "extra column: notes"),
    ("bad_encoding.csv", "bad encoding"),
])
def test_bad_files_are_rejected_with_the_reason(name, reason):
    reasons = check_file(FIXTURES / name, "vendors")
    assert reasons, f"{name} was accepted"
    assert any(r.startswith(reason) for r in reasons), reasons


def test_good_fixture_is_accepted():
    assert check_file(FIXTURES / "good_vendors.csv", "vendors") == []


def test_generator_output_is_accepted(tmp_path):
    write_csv(generate(SMALL), tmp_path)
    for table in COLUMNS:
        assert check_file(tmp_path / f"{table}.csv", table) == [], table


def test_empty_file_and_wrong_order_are_rejected(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert check_file(empty, "vendors")[0].startswith("bad header")
    swapped = tmp_path / "swapped.csv"
    swapped.write_text("vendor_type,vendor_id,vendor_name,phone,street_address,city\n")
    assert check_file(swapped, "vendors") == ["bad header: columns out of contract order"]


def test_unknown_table_is_rejected():
    assert check_file(FIXTURES / "good_vendors.csv", "nope") == ["unknown table: nope"]