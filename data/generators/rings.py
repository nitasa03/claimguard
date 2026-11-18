"""Plant fraud rings and decoys into the synthetic claims world (issue #10, scenario S2).

Reads a ring config (data/generators/config/rings_v1.yaml), modifies existing claims and
claimants in place, and returns the planted truth. Tables and columns stay as in contract v1.
The truth is written to its own folder and is used only for evaluation, never as a feature.
Same seed and config always give the same rings.
"""

from __future__ import annotations

import bisect
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

import yaml

RING_COLUMNS = ["ring_id", "ring_type", "shape", "ring_size", "claim_id", "claimant_id",
                "link_type", "link_id"]
DECOY_COLUMNS = ["decoy_id", "decoy_type", "claim_id", "claimant_id", "link_type", "link_id"]


def load_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def validate(cfg: dict, n_claims: int) -> None:
    """Fail fast on a config that is malformed or plants too much."""
    total = 0
    for name, rt in cfg["ring_types"].items():
        for size, count in rt["rings_per_size"].items():
            if int(size) < 2 or int(count) < 0:
                raise ValueError(f"{name}: bad ring size or count {size}: {count}")
            total += int(size) * int(count)
        for key, p in rt["links"].items():
            if not isinstance(p, bool) and not 0 <= p <= 1:
                raise ValueError(f"{name}: link probability {key}={p} not in [0, 1]")
    if total > cfg["max_ring_claim_share"] * n_claims:
        raise ValueError(f"{total} ring claims exceed max_ring_claim_share of {n_claims} claims")


class _Planter:
    def __init__(self, tables: dict, cfg: dict, seed: int):
        self.t, self.cfg = tables, cfg
        self.rng = random.Random(seed + cfg["seed_offset"])
        self.claimants = {c["claimant_id"]: c for c in tables["claimants"]}
        self.vendors_by_type: dict[str, list[str]] = {}
        for v in tables["vendors"]:
            self.vendors_by_type.setdefault(v["vendor_type"], []).append(v["vendor_id"])
        # claims sorted by loss time, so a time window is a slice
        self.by_time = sorted(tables["claims"], key=lambda c: (c["loss_datetime"], c["claim_id"]))
        self.times = [c["loss_datetime"] for c in self.by_time]
        self.payments_of: dict[str, list[dict]] = {}
        for pay in tables["payments"]:
            self.payments_of.setdefault(pay["claim_id"], []).append(pay)
        self.used_claims: set[str] = set()
        self.used_claimants: set[str] = set()
        self.rings: list[dict] = []
        self.decoys: list[dict] = []

    # --- helpers ---------------------------------------------------------------------

    def _pick_members(self, size: int, window_days: int, types: tuple[str, ...] | None):
        """Pick `size` unused claims with distinct, unused claimants inside one time window."""
        first, last = self.times[0][:10], self.times[-1][:10]
        days = (_d(last) - _d(first)).days - window_days
        for _ in range(200):
            start = _add_days(first, self.rng.randint(0, max(days, 0)))
            lo = bisect.bisect_left(self.times, start)
            hi = bisect.bisect_left(self.times, _add_days(start, window_days))
            pool = [c for c in self.by_time[lo:hi]
                    if c["claim_id"] not in self.used_claims
                    and c["claimant_id"] not in self.used_claimants
                    and (types is None or c["claim_type"] in types)]
            members, seen = [], set()
            for c in self.rng.sample(pool, len(pool)):
                if c["claimant_id"] not in seen:
                    members.append(c)
                    seen.add(c["claimant_id"])
                    if len(members) == size:
                        for m in members:
                            self.used_claims.add(m["claim_id"])
                            self.used_claimants.add(m["claimant_id"])
                        return sorted(members, key=lambda m: m["claim_id"])
        raise ValueError(f"could not find {size} free claims in a {window_days}-day window")

    def _set_repair(self, claim: dict, new_vendor: str) -> None:
        old = claim["repair_vendor_id"]
        claim["repair_vendor_id"] = new_vendor
        for pay in self.payments_of.get(claim["claim_id"], []):
            if old and pay["payee_vendor_id"] == old:
                pay["payee_vendor_id"] = new_vendor

    def _truth(self, ring_id, rtype, shape, size, claim, links):
        for link_type, link_id in links:
            self.rings.append({"ring_id": ring_id, "ring_type": rtype, "shape": shape,
                               "ring_size": size, "claim_id": claim["claim_id"],
                               "claimant_id": claim["claimant_id"],
                               "link_type": link_type, "link_id": link_id})

    # --- ring types ------------------------------------------------------------------

    def staged_collision(self, rt: dict, ring_id: str, size: int) -> None:
        members = self._pick_members(size, rt["window_days"], ("collision", "injury"))
        tow = self.rng.choice(self.vendors_by_type["tow"])
        shop = self.rng.choice(self.vendors_by_type["repair_shop"])
        clinic = self.rng.choice(self.vendors_by_type["clinic"])
        p = rt["links"]
        for c in members:
            c["claim_type"] = "injury" if self.rng.random() < rt["injury_share"] else "collision"
            links = []
            if self.rng.random() < p["tow_vendor"]:
                c["tow_vendor_id"] = tow
                links.append(("tow_vendor", tow))
            if self.rng.random() < p["repair_vendor"]:
                self._set_repair(c, shop)
                links.append(("repair_vendor", shop))
            if c["claim_type"] == "injury" and self.rng.random() < p["clinic_vendor"]:
                c["clinic_vendor_id"] = clinic
                links.append(("clinic_vendor", clinic))
            if not links:  # a member must be linked to the ring by something
                c["tow_vendor_id"] = tow
                links.append(("tow_vendor", tow))
            self._truth(ring_id, "staged_collision", rt["shape"], size, c, links)

    def shared_identity(self, rt: dict, ring_id: str, size: int) -> None:
        members = self._pick_members(size, rt["window_days"], None)
        anchor = self.claimants[members[0]["claimant_id"]]
        if not anchor["phone"]:
            anchor["phone"] = (f"{self.rng.randint(200, 999)}-{self.rng.randint(200, 999)}-"
                               f"{self.rng.randint(0, 9999):04d}")
        address = (anchor["street_address"], anchor["city"], anchor["postal_code"])
        address_id = " | ".join(address)
        p = rt["links"]
        self._truth(ring_id, "shared_identity", rt["shape"], size, members[0],
                    [("phone", anchor["phone"]), ("address", address_id)])
        for c in members[1:]:
            person = self.claimants[c["claimant_id"]]
            share_phone = self.rng.random() < p["phone"]
            share_addr = self.rng.random() < p["address"]
            if p.get("at_least_one") and not (share_phone or share_addr):
                share_phone = True
            links = []
            if share_phone:
                person["phone"] = anchor["phone"]
                links.append(("phone", anchor["phone"]))
            if share_addr:
                person["street_address"], person["city"], person["postal_code"] = address
                links.append(("address", address_id))
            self._truth(ring_id, "shared_identity", rt["shape"], size, c, links)

    # --- observed labels and decoys ----------------------------------------------------

    def relabel_observed(self) -> None:
        """Investigated ring claims are usually, not always, found to be fraud."""
        rate = self.cfg["observed_label"]["fraud_rate_if_investigated"]
        by_id = {c["claim_id"]: c for c in self.t["claims"]}
        denied = set()
        for claim_id in sorted(self.used_claims):
            c = by_id[claim_id]
            if c["fraud_label"] == "":
                continue  # not investigated: stays unlabeled
            c["fraud_label"] = "true" if self.rng.random() < rate else "false"
            if c["fraud_label"] == "true" and c["status"] == "closed_paid":
                c["status"] = "closed_denied"  # a denied claim has no payments
                denied.add(claim_id)
        self.t["payments"][:] = [p for p in self.t["payments"] if p["claim_id"] not in denied]

    def hub_vendor(self, d: dict, n: int) -> None:
        vtype = d["vendor_type"]
        col = {"tow": "tow_vendor_id", "repair_shop": "repair_vendor_id",
               "clinic": "clinic_vendor_id"}[vtype]
        with_vendor = [c for c in self.t["claims"]
                       if c[col] and c["claim_id"] not in self.used_claims]
        avg = len(with_vendor) / len(self.vendors_by_type[vtype])
        target = min(int(avg * d["degree_multiple"]), len(with_vendor))
        hub = self.rng.choice(self.vendors_by_type[vtype])
        chosen = self.rng.sample(with_vendor, target)
        for c in sorted(chosen, key=lambda c: c["claim_id"]):
            if col == "repair_vendor_id":
                self._set_repair(c, hub)
            else:
                c[col] = hub
            self.decoys.append({"decoy_id": f"DECOY-HUB-{n:03d}", "decoy_type": "hub_vendor",
                                "claim_id": c["claim_id"], "claimant_id": c["claimant_id"],
                                "link_type": f"{vtype}_vendor", "link_id": hub})

    def shared_household(self, d: dict, n: int) -> None:
        lo, hi = d["size_range"]
        size = self.rng.randint(lo, hi)
        free = [cid for cid in sorted(self.claimants) if cid not in self.used_claimants]
        group = sorted(self.rng.sample(free, size))
        self.used_claimants.update(group)
        head = self.claimants[group[0]]
        address = (head["street_address"], head["city"], head["postal_code"])
        for cid in group:
            p = self.claimants[cid]
            p["street_address"], p["city"], p["postal_code"] = address
            self.decoys.append({"decoy_id": f"DECOY-HH-{n:03d}", "decoy_type": "shared_household",
                                "claim_id": "", "claimant_id": cid,
                                "link_type": "address", "link_id": " | ".join(address)})


def plant_rings(tables: dict, cfg: dict, seed: int) -> dict:
    """Modify `tables` in place; return the planted truth (rings, decoys, manifest)."""
    validate(cfg, len(tables["claims"]))
    pl = _Planter(tables, cfg, seed)
    n = 0
    for rtype in sorted(cfg["ring_types"]):
        rt = cfg["ring_types"][rtype]
        for size in sorted(int(s) for s in rt["rings_per_size"]):
            for _ in range(int(rt["rings_per_size"][size])):
                n += 1
                getattr(pl, rtype)(rt, f"RING-{n:04d}", size)
    pl.relabel_observed()
    decoys = cfg.get("decoys", {})
    for kind in sorted(decoys):
        for i in range(1, int(decoys[kind]["count"]) + 1):
            getattr(pl, kind)(decoys[kind], i)
    manifest = {"config_version": cfg["version"], "contract": cfg["contract"], "seed": seed,
                "ring_seed": seed + cfg["seed_offset"], "rings": n,
                "ring_claims": len(pl.used_claims),
                "decoy_rows": len(pl.decoys)}
    return {"rings": pl.rings, "decoys": pl.decoys, "manifest": manifest}


def write_truth(truth: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, cols in (("planted_rings", RING_COLUMNS), ("planted_decoys", DECOY_COLUMNS)):
        key = name.removeprefix("planted_")
        with open(out_dir / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(truth[key])
    (out_dir / "manifest.json").write_text(json.dumps(truth["manifest"], indent=2) + "\n")


def _d(iso: str) -> date:
    return date.fromisoformat(iso[:10])


def _add_days(iso_day: str, days: int) -> str:
    return (_d(iso_day) + timedelta(days=days)).isoformat()