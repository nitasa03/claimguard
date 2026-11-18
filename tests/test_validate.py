"""Row-level validation and quarantine (issue #13): bad rows are quarantined with a reason,
good rows pass, and raw rows = valid rows + quarantined rows for every table."""

import copy
import csv
import json

import pytest

from data.contracts.check_file import load_contract
from data.generators.claims_world import generate, write_csv
from data.validation.validate import TableValidator, table_order, validate_dir
from tests.test_claims_world import SMALL

CONTRACT = load_contract()
BASE = generate(SMALL)
KNOWN_KEYS = {"name", "type", "nullable", "pii", "known_at_scoring", "rule", "allowed", "note"}


def run(tmp_path, tables):
    write_csv(tables, tmp_path / "in")
    return validate_dir(tmp_path / "in", tmp_path / "out")


def quarantined(tmp_path, table):
    with open(tmp_path / "out" / "quarantine" / f"{table}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def assert_reconciles(report):
    for table, e in report["tables"].items():
        assert e["reconciles"], table


# --- contract and setup ----------------------------------------------------------------

def test_contract_columns_have_only_known_keys():
    # guards against YAML splitting a value at a comma, e.g. decimal(10,2)
    for table, spec in CONTRACT["tables"].items():
        for col in spec["columns"]:
            assert set(col) <= KNOWN_KEYS, (table, col)


def test_every_contract_rule_is_supported():
    for table in CONTRACT["tables"]:
        TableValidator(CONTRACT, table, {})


def test_unknown_rule_fails_fast():
    contract = copy.deepcopy(CONTRACT)
    contract["tables"]["vendors"]["columns"][0]["rule"] = "looks fine to me"
    with pytest.raises(ValueError, match="unsupported contract rule"):
        TableValidator(contract, "vendors", {})


def test_parents_are_validated_before_children():
    order = table_order(CONTRACT)
    assert order.index("policies") < order.index("claims") < order.index("payments")
    assert order.index("vendors") < order.index("claims")


# --- clean data --------------------------------------------------------------------------

def test_generator_output_is_all_valid(tmp_path):
    report = run(tmp_path, copy.deepcopy(BASE))
    for table, e in report["tables"].items():
        assert e["status"] == "loaded", table
        assert e["quarantined_rows"] == 0, (table, e["reasons"])
        assert e["valid_rows"] == len(BASE[table])
    assert_reconciles(report)
    saved = json.loads((tmp_path / "out" / "report.json").read_text())
    assert saved == report


# --- one bad value, one reason ------------------------------------------------------------

@pytest.mark.parametrize("table, i, column, value, reason", [
    ("claimants", 0, "full_name", "", "full_name: null"),
    ("claimants", 1, "phone", "12345", "phone: pattern"),
    ("vehicles", 0, "model_year", "1985", "model_year: range"),
    ("vehicles", 1, "model_year", "abc", "model_year: type"),
    ("policies", 0, "coverage_type", "gold", "coverage_type: allowed"),
    ("policies", 1, "annual_premium", "12.345", "annual_premium: type"),
    ("policies", 2, "policy_end_date", "2000-01-01", "policy_end_date: compare"),
    ("claims", 0, "report_datetime", "2000-01-01T00:00:00Z", "report_datetime: compare"),
    ("claims", 1, "loss_datetime", "2031-01-01T00:00:00Z", "loss_datetime: policy_period"),
    ("claims", 2, "claimed_amount", "-5.00", "claimed_amount: compare"),
    ("claims", 3, "policy_id", "POL-99999999", "policy_id: fk"),
    ("claims", 4, "fraud_label", "yes", "fraud_label: type"),
    ("claims", 5, "loss_datetime", "2025-01-01 10:00", "loss_datetime: type"),
    ("payments", 0, "paid_amount", "0.00", "paid_amount: compare"),
    ("payments", 1, "paid_date", "2000-01-01", "paid_date: compare"),
])
def test_bad_value_is_quarantined_with_its_reason(tmp_path, table, i, column, value, reason):
    tables = copy.deepcopy(BASE)
    tables[table][i][column] = value
    report = run(tmp_path, tables)
    entry = report["tables"][table]
    assert entry["quarantined_rows"] >= 1
    assert entry["valid_rows"] <= len(BASE[table]) - 1
    assert reason in entry["reasons"], entry["reasons"]
    bad = [r for r in quarantined(tmp_path, table) if r["_source_line"] == str(i + 2)]
    assert bad and reason in bad[0]["_reasons"]
    assert_reconciles(report)


def test_vendor_of_wrong_type_is_rejected(tmp_path):
    tables = copy.deepcopy(BASE)
    clinic = next(v["vendor_id"] for v in tables["vendors"] if v["vendor_type"] == "clinic")
    claim = next(c for c in tables["claims"] if c["tow_vendor_id"])
    claim["tow_vendor_id"] = clinic
    report = run(tmp_path, tables)
    assert report["tables"]["claims"]["reasons"].get("tow_vendor_id: fk") == 1


def test_all_reasons_in_a_row_are_listed(tmp_path):
    tables = copy.deepcopy(BASE)
    tables["vendors"][0].update(vendor_type="bakery", vendor_name="")
    run(tmp_path, tables)
    (row,) = quarantined(tmp_path, "vendors")
    assert "vendor_name: null" in row["_reasons"]
    assert "vendor_type: allowed" in row["_reasons"]


# --- across tables --------------------------------------------------------------------------

def test_children_of_a_quarantined_parent_are_quarantined(tmp_path):
    tables = copy.deepcopy(BASE)
    paid = tables["payments"][0]["claim_id"]
    claim = next(c for c in tables["claims"] if c["claim_id"] == paid)
    claim["claim_type"] = "meteor"
    report = run(tmp_path, tables)
    n_payments = sum(p["claim_id"] == paid for p in tables["payments"])
    assert report["tables"]["claims"]["quarantined_rows"] == 1
    assert report["tables"]["payments"]["reasons"]["claim_id: fk"] == n_payments
    assert_reconciles(report)


def test_rejected_file_loads_no_rows(tmp_path):
    write_csv(copy.deepcopy(BASE), tmp_path / "in")
    path = tmp_path / "in" / "payments.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0] + ",extra"] + lines[1:]) + "\n")
    report = validate_dir(tmp_path / "in", tmp_path / "out")
    entry = report["tables"]["payments"]
    assert entry["status"] == "rejected"
    assert entry["file_reasons"] == ["extra column: extra"]
    assert entry["valid_rows"] == entry["quarantined_rows"] == 0
    assert_reconciles(report)


def test_same_input_gives_identical_output(tmp_path):
    run(tmp_path / "a", copy.deepcopy(BASE))
    run(tmp_path / "b", copy.deepcopy(BASE))
    for sub in ("valid", "quarantine"):
        for f in sorted((tmp_path / "a" / "out" / sub).iterdir()):
            assert f.read_bytes() == (tmp_path / "b" / "out" / sub / f.name).read_bytes()