"""File-level checks against the claims-world data contract (issue #11).

A file that fails any check is rejected whole (contract `on_failure.file_level`).
Row-level checks (types, nulls, patterns, keys) and quarantine belong to validation (#13).

Usage:
    python -m data.contracts.check_file .local/claims_world/vendors.csv vendors
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import yaml

CONTRACT_PATH = Path(__file__).with_name("claims_world_v1.yaml")


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_file(path: str | Path, table: str, contract: dict | None = None) -> list[str]:
    """Return the reasons to reject the file; an empty list means accepted."""
    contract = contract or load_contract()
    if table not in contract["tables"]:
        return [f"unknown table: {table}"]
    fmt = contract["file_format"]
    raw = Path(path).read_bytes()
    try:
        text = raw.decode(fmt["encoding"])
    except UnicodeDecodeError as e:
        return [f"bad encoding: not {fmt['encoding']} (byte {e.start})"]

    header = next(csv.reader(io.StringIO(text), delimiter=fmt["delimiter"]), None)
    if not header:
        return ["bad header: file is empty or has no header row"]

    expected = [c["name"] for c in contract["tables"][table]["columns"]]
    missing = [c for c in expected if c not in header]
    extra = [c for c in header if c not in expected]
    reasons = []
    if missing:
        reasons.append(f"missing column: {', '.join(missing)}")
    if extra:
        reasons.append(f"extra column: {', '.join(extra)}")
    if len(set(header)) != len(header):
        reasons.append("bad header: duplicate column names")
    if not reasons and header != expected:
        reasons.append("bad header: columns out of contract order")
    return reasons


def main() -> None:
    path, table = sys.argv[1], sys.argv[2]
    reasons = check_file(path, table)
    if reasons:
        print(f"REJECTED {path}: " + "; ".join(reasons))
        sys.exit(1)
    print(f"ACCEPTED {path}")


if __name__ == "__main__":
    main()