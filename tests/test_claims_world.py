"""Unit tests for the synthetic claims-world generator (issue #9).

Uses a small world so the suite runs in seconds. Column names, nulls, patterns and
allowed values are read from the data contract, so the tests follow the contract.
"""

import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

from data.generators.claims_world import COLUMNS, Settings, generate, write_csv

CONTRACT = yaml.safe_load(Path("data/contracts/claims_world_v1.yaml").read_text())
SMALL = Settings(seed=7, n_claims=3_000, n_policies=1_500, n_tow=20, n_repair=30, n_clinic=10)


@pytest.fixture(scope="module")
def world():
    return generate(SMALL)


def contract_columns(table):
    return CONTRACT["tables"][table]["columns"]


# --- repeatability -------------------------------------------------------------

def test_same_seed_gives_identical_files(tmp_path):
    write_csv(generate(SMALL), tmp_path / "a")
    write_csv(generate(SMALL), tmp_path / "b")
    for name in COLUMNS:
        assert (tmp_path / "a" / f"{name}.csv").read_bytes() == (
            tmp_path / "b" / f"{name}.csv"
        ).read_bytes(), name


def test_different_seed_gives_different_data():
    other = generate(Settings(**{**SMALL.__dict__, "seed": 8}))
    assert other["claims"] != generate(SMALL)["claims"]


# --- shape and contract ----------------------------------------------------------

def test_row_counts(world):
    assert len(world["claims"]) == SMALL.n_claims
    assert len(world["policies"]) == SMALL.n_policies
    assert len(world["vendors"]) == SMALL.n_tow + SMALL.n_repair + SMALL.n_clinic


@pytest.mark.parametrize("table", list(COLUMNS))
def test_columns_match_contract(table):
    assert COLUMNS[table] == [c["name"] for c in contract_columns(table)]


@pytest.mark.parametrize("table", list(COLUMNS))
def test_primary_keys_unique(world, table):
    (pk,) = CONTRACT["tables"][table]["primary_key"]
    counts = Counter(row[pk] for row in world[table])
    assert max(counts.values()) == 1


@pytest.mark.parametrize("table", list(COLUMNS))
def test_contract_nulls_patterns_and_allowed_values(world, table):
    for col in contract_columns(table):
        values = [str(row[col["name"]]) for row in world[table]]
        if not col["nullable"]:
            assert all(v != "" for v in values), f"{table}.{col['name']} has nulls"
        rule = col.get("rule", "")
        if rule.startswith("^") and "normaliz" not in rule:
            bad = [v for v in values if v and not re.match(rule, v)]
            assert not bad, f"{table}.{col['name']} pattern fails: {bad[:3]}"
        if "allowed" in col:
            assert set(values) <= set(col["allowed"]), f"{table}.{col['name']}"


def test_phone_has_ten_digits_after_normalizing(world):
    for row in world["claimants"]:
        if row["phone"]:
            assert re.fullmatch(r"[0-9]{10}", re.sub(r"\D", "", row["phone"]))


# --- links between tables ----------------------------------------------------------

def test_foreign_keys(world):
    policies = {p["policy_id"]: p for p in world["policies"]}
    vendor_type = {v["vendor_id"]: v["vendor_type"] for v in world["vendors"]}
    claim_ids = {c["claim_id"] for c in world["claims"]}
    for c in world["claims"]:
        p = policies[c["policy_id"]]
        assert (c["claimant_id"], c["vehicle_id"]) == (p["claimant_id"], p["vehicle_id"])
        for col, vtype in (("tow_vendor_id", "tow"), ("repair_vendor_id", "repair_shop"),
                           ("clinic_vendor_id", "clinic")):
            if c[col]:
                assert vendor_type[c[col]] == vtype
    for pay in world["payments"]:
        assert pay["claim_id"] in claim_ids
        assert not pay["payee_vendor_id"] or pay["payee_vendor_id"] in vendor_type


# --- business rules ------------------------------------------------------------------

def test_dates_are_consistent(world):
    policies = {p["policy_id"]: p for p in world["policies"]}
    for p in world["policies"]:
        assert p["policy_end_date"] > p["policy_start_date"]
    for c in world["claims"]:
        p = policies[c["policy_id"]]
        assert p["policy_start_date"] <= c["loss_datetime"][:10] <= p["policy_end_date"]
        assert c["report_datetime"] >= c["loss_datetime"]  # ISO strings sort as times


def test_payments_only_for_paid_claims_and_not_above_claimed(world):
    claims = {c["claim_id"]: c for c in world["claims"]}
    paid = Counter()
    for pay in world["payments"]:
        c = claims[pay["claim_id"]]
        assert c["status"] == "closed_paid"
        assert float(pay["paid_amount"]) > 0
        assert pay["paid_date"] >= c["report_datetime"][:10]
        paid[pay["claim_id"]] += float(pay["paid_amount"])
    for claim_id, total in paid.items():
        assert total <= float(claims[claim_id]["claimed_amount"]) + 0.01


def test_fraud_label_only_on_investigated_claims(world):
    labels = Counter(c["fraud_label"] for c in world["claims"])
    assert labels[""] > labels["true"] + labels["false"]  # most claims are not investigated
    assert labels["true"] > 0