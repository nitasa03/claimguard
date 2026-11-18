"""Tests for planted fraud rings and decoys (issue #10, scenario S2).

Uses the small world from the generator tests and a scaled-down copy of the ring config.
"""

import copy
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

from data.generators.claims_world import COLUMNS, generate, write_csv
from data.generators.rings import load_config, plant_rings, validate, write_truth
from tests import test_claims_world as base
from tests.test_claims_world import SMALL

CONFIG_PATH = Path("data/generators/config/rings_v1.yaml")
FULL = load_config(CONFIG_PATH)


def small_config():
    cfg = copy.deepcopy(FULL)
    cfg["max_ring_claim_share"] = 0.05
    cfg["ring_types"]["staged_collision"]["rings_per_size"] = {3: 4, 5: 2, 10: 1}
    cfg["ring_types"]["shared_identity"]["rings_per_size"] = {3: 3, 5: 2, 10: 1}
    cfg["decoys"]["shared_household"]["count"] = 5
    return cfg


CFG = small_config()


@pytest.fixture(scope="module")
def planted():
    tables = generate(SMALL)
    truth = plant_rings(tables, CFG, SMALL.seed)
    return tables, truth


def rings_by_id(truth):
    rings = defaultdict(list)
    for row in truth["rings"]:
        rings[row["ring_id"]].append(row)
    return rings


# --- config -------------------------------------------------------------------------

def test_full_config_is_valid_for_the_full_world():
    validate(FULL, 100_000)


def test_full_config_uses_the_s2_ring_sizes():
    for rt in FULL["ring_types"].values():
        assert sorted(int(s) for s in rt["rings_per_size"]) == [3, 5, 10]  # AT-S2-1


def test_guard_rejects_too_many_ring_claims():
    with pytest.raises(ValueError, match="max_ring_claim_share"):
        validate(FULL, 10_000)


def test_guard_rejects_bad_probability():
    cfg = small_config()
    cfg["ring_types"]["shared_identity"]["links"]["phone"] = 1.5
    with pytest.raises(ValueError, match="not in"):
        validate(cfg, SMALL.n_claims)


# --- rings --------------------------------------------------------------------------

def test_ring_counts_and_sizes_match_config(planted):
    _, truth = planted
    found = defaultdict(int)
    for rows in rings_by_id(truth).values():
        claims = {r["claim_id"] for r in rows}
        assert len(claims) == rows[0]["ring_size"]
        assert len({r["claimant_id"] for r in rows}) == rows[0]["ring_size"]  # one claimant each
        found[(rows[0]["ring_type"], rows[0]["ring_size"])] += 1
    for rtype, rt in CFG["ring_types"].items():
        for size, count in rt["rings_per_size"].items():
            assert found[(rtype, int(size))] == count


def test_no_claim_or_claimant_is_in_two_rings(planted):
    _, truth = planted
    owner = {}
    for r in truth["rings"]:
        for key in (r["claim_id"], r["claimant_id"]):
            assert owner.setdefault(key, r["ring_id"]) == r["ring_id"]


def test_members_really_share_the_linking_entity(planted):
    tables, truth = planted
    claims = {c["claim_id"]: c for c in tables["claims"]}
    people = {p["claimant_id"]: p for p in tables["claimants"]}
    column = {"tow_vendor": "tow_vendor_id", "repair_vendor": "repair_vendor_id",
              "clinic_vendor": "clinic_vendor_id"}
    for r in truth["rings"]:
        if r["link_type"] in column:
            assert claims[r["claim_id"]][column[r["link_type"]]] == r["link_id"]
        elif r["link_type"] == "phone":
            assert people[r["claimant_id"]]["phone"] == r["link_id"]
        else:
            p = people[r["claimant_id"]]
            assert " | ".join((p["street_address"], p["city"], p["postal_code"])) == r["link_id"]


def test_every_ring_link_is_shared_by_at_least_two_members(planted):
    _, truth = planted
    for rows in rings_by_id(truth).values():
        members = defaultdict(set)
        for r in rows:
            members[(r["link_type"], r["link_id"])].add(r["claim_id"])
        assert max(len(m) for m in members.values()) >= 2


def test_ring_claims_fall_inside_the_window(planted):
    tables, truth = planted
    claims = {c["claim_id"]: c for c in tables["claims"]}
    for rows in rings_by_id(truth).values():
        days = [date.fromisoformat(claims[r["claim_id"]]["loss_datetime"][:10]) for r in rows]
        window = CFG["ring_types"][rows[0]["ring_type"]]["window_days"]
        assert (max(days) - min(days)).days <= window


# --- decoys -------------------------------------------------------------------------

def test_hub_decoy_has_high_degree_and_no_ring_claims(planted):
    tables, truth = planted
    hub_rows = [d for d in truth["decoys"] if d["decoy_type"] == "hub_vendor"]
    hub = hub_rows[0]["link_id"]
    tow_claims = [c for c in tables["claims"] if c["tow_vendor_id"]]
    avg = len(tow_claims) / SMALL.n_tow
    assert sum(c["tow_vendor_id"] == hub for c in tow_claims) >= 5 * avg
    ring_claims = {r["claim_id"] for r in truth["rings"]}
    assert not ring_claims & {d["claim_id"] for d in hub_rows}


def test_households_share_an_address_and_are_not_ring_members(planted):
    _, truth = planted
    homes = defaultdict(set)
    for d in truth["decoys"]:
        if d["decoy_type"] == "shared_household":
            homes[d["decoy_id"]].add(d["link_id"])
    assert len(homes) == CFG["decoys"]["shared_household"]["count"]
    assert all(len(addresses) == 1 for addresses in homes.values())
    ring_people = {r["claimant_id"] for r in truth["rings"]}
    household_people = {d["claimant_id"] for d in truth["decoys"]
                        if d["decoy_type"] == "shared_household"}
    assert not ring_people & household_people


# --- contract, labels, repeatability, separation ------------------------------------

def test_planted_world_still_passes_the_generator_checks(planted):
    tables, _ = planted
    for table in COLUMNS:
        base.test_contract_nulls_patterns_and_allowed_values(tables, table)
    base.test_phone_has_ten_digits_after_normalizing(tables)
    base.test_foreign_keys(tables)
    base.test_dates_are_consistent(tables)
    base.test_payments_only_for_paid_claims_and_not_above_claimed(tables)
    base.test_fraud_label_only_on_investigated_claims(tables)


def test_investigated_ring_claims_are_mostly_labeled_fraud(planted):
    tables, truth = planted
    ring_claims = {r["claim_id"] for r in truth["rings"]}
    labels = [c["fraud_label"] for c in tables["claims"]
              if c["claim_id"] in ring_claims and c["fraud_label"]]
    if labels:
        assert labels.count("true") >= labels.count("false")


def test_same_seed_gives_identical_truth_and_tables(planted):
    tables, truth = planted
    tables2 = generate(SMALL)
    truth2 = plant_rings(tables2, CFG, SMALL.seed)
    assert truth2 == truth
    assert tables2 == tables


def test_truth_is_written_apart_from_the_tables(planted, tmp_path):
    tables, truth = planted
    write_csv(tables, tmp_path / "world")
    write_truth(truth, tmp_path / "truth")
    assert sorted(p.name for p in (tmp_path / "world").iterdir()) == sorted(
        f"{n}.csv" for n in COLUMNS)
    assert sorted(p.name for p in (tmp_path / "truth").iterdir()) == [
        "manifest.json", "planted_decoys.csv", "planted_rings.csv"]
    for name in COLUMNS:
        header = (tmp_path / "world" / f"{name}.csv").read_text().splitlines()[0]
        assert "ring" not in header and "decoy" not in header