"""Synthetic claims-world generator v1 (issue #9).

Seeded and repeatable: the same seed and settings always produce identical files.
Output follows data/contracts/claims_world_v1.yaml. All data is synthetic.

Usage:
    python -m data.generators.claims_world --seed 42 --n-claims 100000 --out .local/claims_world
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from faker import Faker

CONTRACT_VERSION = "1.0.0"
REFERENCE_DATE = date(2026, 1, 1)  # fixed, so ages never depend on today's date

VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"  # no I, O or Q
MAKES = {
    "Toyota": ["Corolla", "RAV4", "Camry"],
    "Honda": ["Civic", "CR-V", "Accord"],
    "Ford": ["F-150", "Escape", "Focus"],
    "Hyundai": ["Elantra", "Tucson"],
    "Chevrolet": ["Silverado", "Equinox"],
}
CITIES = ["Toronto", "Mississauga", "Brampton", "Hamilton", "Ottawa", "London", "Markham"]
COVERAGE = ["liability", "collision", "comprehensive"]
CLAIM_TYPES = ["collision", "theft", "glass", "injury"]
CLAIM_TYPE_WEIGHTS = [0.70, 0.08, 0.12, 0.10]
# log-normal (mu, sigma) of claimed amount per claim type
AMOUNT_PARAMS = {
    "collision": (8.3, 0.6),
    "theft": (9.5, 0.5),
    "glass": (6.5, 0.4),
    "injury": (9.2, 0.7),
}

COLUMNS = {
    "policies": ["policy_id", "claimant_id", "vehicle_id", "policy_start_date",
                 "policy_end_date", "coverage_type", "annual_premium"],
    "claimants": ["claimant_id", "full_name", "date_of_birth", "phone", "email",
                  "street_address", "city", "postal_code"],
    "vehicles": ["vehicle_id", "vin", "make", "model", "model_year"],
    "vendors": ["vendor_id", "vendor_type", "vendor_name", "phone", "street_address", "city"],
    "claims": ["claim_id", "policy_id", "claimant_id", "vehicle_id", "loss_datetime",
               "report_datetime", "loss_city", "claim_type", "claimed_amount", "tow_vendor_id",
               "repair_vendor_id", "clinic_vendor_id", "police_report", "status", "fraud_label"],
    "payments": ["payment_id", "claim_id", "payee_vendor_id", "paid_amount", "paid_date"],
}


@dataclass(frozen=True)
class Settings:
    seed: int = 42
    n_claims: int = 100_000
    n_policies: int = 60_000
    n_tow: int = 300
    n_repair: int = 500
    n_clinic: int = 200
    start: date = date(2024, 1, 1)
    end: date = date(2025, 12, 31)
    investigated_rate: float = 0.15
    fraud_rate_if_investigated: float = 0.30


def _phone(rng: random.Random) -> str:
    return f"{rng.randint(200, 999)}-{rng.randint(200, 999)}-{rng.randint(0, 9999):04d}"


def _vin(rng: random.Random) -> str:
    return "".join(rng.choice(VIN_CHARS) for _ in range(17))


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _money(x: float) -> str:
    return f"{x:.2f}"


def _bool(x: bool | None) -> str:
    return "" if x is None else ("true" if x else "false")


def generate(s: Settings) -> dict[str, list[dict]]:
    """Build all tables in memory. Pure function of the settings."""
    rng = random.Random(s.seed)
    fake = Faker("en_CA")
    fake.seed_instance(s.seed)

    claimants, vehicles, policies = [], [], []
    for i in range(1, s.n_policies + 1):
        cid, vid, pid = f"CLT-{i:08d}", f"VEH-{i:08d}", f"POL-{i:08d}"
        age_days = rng.randint(18 * 365, 85 * 365)
        claimants.append({
            "claimant_id": cid,
            "full_name": fake.name(),
            "date_of_birth": (REFERENCE_DATE - timedelta(days=age_days)).isoformat(),
            "phone": _phone(rng) if rng.random() > 0.03 else "",
            "email": fake.email(safe=True) if rng.random() > 0.10 else "",
            "street_address": fake.street_address(),
            "city": rng.choice(CITIES),
            "postal_code": fake.postcode(),
        })
        make = rng.choice(list(MAKES))
        vehicles.append({
            "vehicle_id": vid,
            "vin": _vin(rng),
            "make": make,
            "model": rng.choice(MAKES[make]),
            "model_year": rng.randint(2005, 2026),
        })
        # start between ~10 months before the window and 30 days before its end
        span = (s.end - s.start).days + 300 - 30
        p_start = s.start - timedelta(days=300) + timedelta(days=rng.randint(0, span))
        policies.append({
            "policy_id": pid,
            "claimant_id": cid,
            "vehicle_id": vid,
            "policy_start_date": p_start.isoformat(),
            "policy_end_date": (p_start + timedelta(days=365)).isoformat(),
            "coverage_type": rng.choice(COVERAGE),
            "annual_premium": _money(rng.uniform(900, 3500)),
        })

    vendors, by_type = [], {"tow": [], "repair_shop": [], "clinic": []}
    n = 0
    for vtype, count in (("tow", s.n_tow), ("repair_shop", s.n_repair), ("clinic", s.n_clinic)):
        for _ in range(count):
            n += 1
            vid = f"VND-{n:06d}"
            vendors.append({
                "vendor_id": vid,
                "vendor_type": vtype,
                "vendor_name": fake.company(),
                "phone": _phone(rng),
                "street_address": fake.street_address(),
                "city": rng.choice(CITIES),
            })
            by_type[vtype].append(vid)

    claims, payments = [], []
    pay_n = 0
    for i in range(1, s.n_claims + 1):
        pol = policies[rng.randrange(s.n_policies)]
        p_start = date.fromisoformat(pol["policy_start_date"])
        p_end = date.fromisoformat(pol["policy_end_date"])
        lo, hi = max(p_start, s.start), min(p_end, s.end)
        loss_day = lo + timedelta(days=rng.randint(0, (hi - lo).days))
        loss = datetime.combine(loss_day, time(0), tzinfo=UTC) + timedelta(
            minutes=rng.randint(0, 24 * 60 - 1))
        report = loss + timedelta(hours=min(rng.expovariate(1 / 30), 24 * 30))

        ctype = rng.choices(CLAIM_TYPES, CLAIM_TYPE_WEIGHTS)[0]
        mu, sigma = AMOUNT_PARAMS[ctype]
        amount = round(rng.lognormvariate(mu, sigma), 2)
        tow = rng.choice(by_type["tow"]) if ctype == "collision" and rng.random() < 0.6 else ""
        repair = (rng.choice(by_type["repair_shop"])
                  if ctype in ("collision", "glass") and rng.random() < 0.9 else "")
        clinic = (rng.choice(by_type["clinic"])
                  if ctype == "injury" or (ctype == "collision" and rng.random() < 0.1) else "")

        fraud = None
        if rng.random() < s.investigated_rate:
            fraud = rng.random() < s.fraud_rate_if_investigated
        if report.date() > s.end - timedelta(days=30):
            status = "open"
        elif fraud or rng.random() < 0.05:
            status = "closed_denied"
        else:
            status = "closed_paid"

        claim_id = f"CLM-{i:09d}"
        claims.append({
            "claim_id": claim_id,
            "policy_id": pol["policy_id"],
            "claimant_id": pol["claimant_id"],
            "vehicle_id": pol["vehicle_id"],
            "loss_datetime": _ts(loss),
            "report_datetime": _ts(report),
            "loss_city": rng.choice(CITIES),
            "claim_type": ctype,
            "claimed_amount": _money(amount),
            "tow_vendor_id": tow,
            "repair_vendor_id": repair,
            "clinic_vendor_id": clinic,
            "police_report": _bool(rng.random() < 0.55),
            "status": status,
            "fraud_label": _bool(fraud),
        })

        if status == "closed_paid":
            total = amount * rng.uniform(0.6, 1.0)
            parts = [total] if rng.random() < 0.7 else [total * 0.6, total * 0.4]
            for part in parts:
                pay_n += 1
                payments.append({
                    "payment_id": f"PAY-{pay_n:09d}",
                    "claim_id": claim_id,
                    "payee_vendor_id": repair if repair and rng.random() < 0.7 else "",
                    "paid_amount": _money(part),
                    "paid_date": (report.date() + timedelta(days=rng.randint(5, 60))).isoformat(),
                })

    return {"policies": policies, "claimants": claimants, "vehicles": vehicles,
            "vendors": vendors, "claims": claims, "payments": payments}


def write_csv(tables: dict[str, list[dict]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        with open(out_dir / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS[name], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate the synthetic claims world (CSV).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-claims", type=int, default=100_000)
    p.add_argument("--n-policies", type=int, default=60_000)
    p.add_argument("--out", type=Path, default=Path(".local/claims_world"))
    a = p.parse_args()
    s = Settings(seed=a.seed, n_claims=a.n_claims, n_policies=a.n_policies)
    tables = generate(s)
    write_csv(tables, a.out)
    print({k: len(v) for k, v in tables.items()}, "->", a.out)


if __name__ == "__main__":
    main()
