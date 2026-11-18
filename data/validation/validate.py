"""Row-level validation and quarantine against the claims-world contract (issue #13).

Each file first passes the file-level checks (#11); a rejected file loads no rows.
Each row is then checked for nulls, types, patterns, allowed values, ranges, same-row
comparisons, foreign keys and cross-table rules. Valid rows go on; invalid rows go to
quarantine with every reason found. Per table, raw rows = valid rows + quarantined rows.

Foreign keys are checked against the valid rows of the parent table, so a child of a
quarantined parent is quarantined too (no orphans). Duplicates are not removed here (#14).

Usage:
    python -m data.validation.validate --in .local/claims_world --out .local/validated
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from data.contracts.check_file import check_file, load_contract

REASON_COLUMNS = ["_source_line", "_reasons"]
_COMPARE = re.compile(r"^(>=|>|<=|<) (\S+)$")
_RANGE = re.compile(r"^(-?\d+) to (-?\d+)$")
_FK = re.compile(r"^FK (\w+)\.(\w+)$")
_FK_TYPED = re.compile(r"^FK (\w+) where type = (\w+)$")
_DECIMAL = re.compile(r"^decimal\((\d+),(\d+)\)$")


# --- single values -------------------------------------------------------------------

def type_error(value: str, ctype: str) -> str | None:
    """Return why `value` is not of contract type `ctype`, or None."""
    try:
        if ctype == "string":
            return None
        if ctype == "integer":
            int(value)
        elif ctype == "boolean":
            if value not in ("true", "false"):
                return "not true or false"
        elif ctype == "date":
            date.fromisoformat(value)
            if len(value) != 10:
                return "not YYYY-MM-DD"
        elif ctype == "timestamp":
            if not value.endswith("Z"):
                return "not UTC (no Z)"
            datetime.fromisoformat(value[:-1])
        elif m := _DECIMAL.match(ctype):
            precision, scale = int(m[1]), int(m[2])
            d = Decimal(value)
            digits, exponent = d.as_tuple().digits, d.as_tuple().exponent
            if not d.is_finite() or -exponent > scale or len(digits) > precision:
                return f"not {ctype}"
        else:
            raise ValueError(f"unknown contract type {ctype}")
    except (ValueError, InvalidOperation):
        return f"not {ctype}"
    return None


def _as_comparable(value: str, ctype: str):
    if ctype.startswith("decimal") or ctype == "integer":
        return Decimal(value)
    return value[:10] if ctype == "date" else value


def _compare(left, op: str, right) -> bool:
    return {">": left > right, ">=": left >= right, "<": left < right, "<=": left <= right}[op]


# --- a table ---------------------------------------------------------------------------

class TableValidator:
    """Checks the rows of one table; `valid` holds the parent tables' valid rows by key."""

    def __init__(self, contract: dict, table: str, valid: dict[str, dict[str, dict]]):
        self.table = table
        self.spec = contract["tables"][table]
        self.columns = {c["name"]: c for c in self.spec["columns"]}
        self.valid = valid
        for col in self.spec["columns"]:  # fail fast on a rule this code does not know
            if rule := col.get("rule"):
                self._rule_kind(rule)

    def _rule_kind(self, rule: str) -> str:
        if rule.startswith("^"):
            return "pattern"
        if _COMPARE.match(rule):
            return "compare"
        if _RANGE.match(rule):
            return "range"
        if _FK.match(rule) or _FK_TYPED.match(rule):
            return "fk"
        if rule == "within policy period":
            return "policy_period"
        raise ValueError(f"{self.table}: unsupported contract rule: {rule}")

    def _parent_row(self, row: dict, parent: str) -> dict | None:
        """The valid parent row this row points to through its FK column."""
        for name, col in self.columns.items():
            m = _FK.match(col.get("rule", ""))
            if m and m[1] == parent and row[name]:
                return self.valid.get(parent, {}).get(row[name])
        return None

    def check_row(self, row: dict) -> list[tuple[str, str, str]]:
        """Return every problem as (column, code, detail); an empty list means valid."""
        problems = []
        for name, col in self.columns.items():
            value = row[name]
            if value == "":
                if not col["nullable"]:
                    problems.append((name, "null", "required value missing"))
                continue
            if err := type_error(value, col["type"]):
                problems.append((name, "type", err))
                continue
            if "allowed" in col and value not in col["allowed"]:
                problems.append((name, "allowed", f"{value} not in {col['allowed']}"))
            rule = col.get("rule")
            if rule and (err := self._check_rule(row, name, col, rule)):
                    problems.append((name, self._rule_kind(rule), err))
        return problems

    def _check_rule(self, row: dict, name: str, col: dict, rule: str) -> str | None:
        value, kind = row[name], self._rule_kind(rule)
        if kind == "pattern":
            pattern = rule.split(" after ")[0]
            if "after normaliz" in rule:
                value = re.sub(r"\D", "", value)
            return None if re.match(pattern, value) else f"pattern {pattern}"
        if kind == "range":
            lo, hi = map(int, _RANGE.match(rule).groups())
            return None if lo <= int(value) <= hi else f"out of range {lo} to {hi}"
        if kind == "fk":
            if m := _FK_TYPED.match(rule):
                parent = self.valid.get(m[1], {}).get(value)
                if parent is None:
                    return f"no valid {m[1]} row {value}"
                return None if parent["vendor_type"] == m[2] else f"vendor type is not {m[2]}"
            m = _FK.match(rule)
            return None if value in self.valid.get(m[1], {}) else f"no valid {m[1]} row {value}"
        if kind == "policy_period":
            policy = self._parent_row(row, "policies")
            if policy is None:
                return None  # the policy_id FK check already reports this
            day = value[:10]
            ok = policy["policy_start_date"] <= day <= policy["policy_end_date"]
            return None if ok else "outside policy period"
        op, ref = _COMPARE.match(rule).groups()
        if "." in ref:  # another table, reached through this row's foreign key
            parent_table, parent_col = ref.split(".")
            parent = self._parent_row(row, parent_table)
            if parent is None:
                return None
            other, other_type = parent[parent_col], "string"
        elif ref in self.columns:  # same row
            other, other_type = row[ref], self.columns[ref]["type"]
            if other == "" or type_error(other, other_type):
                return None  # that column reports its own problem
        else:  # a number
            other, other_type = ref, "decimal(38,10)"
        left = _as_comparable(value, col["type"])
        right = _as_comparable(other, other_type)
        if isinstance(left, str) and isinstance(right, str):
            left, right = left[: len(right)], right[: len(left)]  # date vs timestamp
        return None if _compare(left, op, right) else f"not {op} {ref}"


# --- a run ---------------------------------------------------------------------------

def table_order(contract: dict) -> list[str]:
    """Parents before children, from the FK rules in the contract."""
    deps = {}
    for table, spec in contract["tables"].items():
        deps[table] = set()
        for col in spec["columns"]:
            m = _FK.match(col.get("rule", "")) or _FK_TYPED.match(col.get("rule", ""))
            if m and m[1] != table:
                deps[table].add(m[1])
    order: list[str] = []
    while len(order) < len(deps):
        ready = sorted(t for t in deps if t not in order and deps[t] <= set(order))
        if not ready:
            raise ValueError("circular foreign keys in contract")
        order.extend(ready)
    return order


def validate_dir(in_dir: Path, out_dir: Path, contract: dict | None = None) -> dict:
    """Validate every contract table in `in_dir`; write valid and quarantine CSVs and a report."""
    contract = contract or load_contract()
    valid: dict[str, dict[str, dict]] = {}
    report = {"contract_version": str(contract["version"]), "tables": {}}
    for table in table_order(contract):
        path = in_dir / f"{table}.csv"
        names = [c["name"] for c in contract["tables"][table]["columns"]]
        (pk,) = contract["tables"][table]["primary_key"]
        file_reasons = check_file(path, table, contract) if path.exists() else ["file missing"]
        entry = {"status": "rejected" if file_reasons else "loaded",
                 "file_reasons": file_reasons, "raw_rows": 0, "valid_rows": 0,
                 "quarantined_rows": 0, "reasons": {}}
        valid[table] = {}
        if not file_reasons:
            checker = TableValidator(contract, table, valid)
            good, bad, reasons = [], [], Counter()
            with open(path, encoding="utf-8", newline="") as f:
                for line, row in enumerate(csv.DictReader(f), start=2):
                    found = checker.check_row(row)
                    if found:
                        text = "; ".join(f"{c}: {code}: {detail}" for c, code, detail in found)
                        bad.append({**row, "_source_line": line, "_reasons": text})
                        reasons.update(f"{c}: {code}" for c, code, _ in found)
                    else:
                        good.append(row)
                        valid[table].setdefault(row[pk], row)
            _write(out_dir / "valid" / f"{table}.csv", names, good)
            _write(out_dir / "quarantine" / f"{table}.csv", names + REASON_COLUMNS, bad)
            entry.update(raw_rows=_count_rows(path), valid_rows=len(good),
                         quarantined_rows=len(bad), reasons=dict(sorted(reasons.items())))
        entry["reconciles"] = entry["raw_rows"] == entry["valid_rows"] + entry["quarantined_rows"]
        report["tables"][table] = entry
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def _count_rows(path: Path) -> int:
    """Count data rows in a separate pass, so the reconciliation is an independent check."""
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def _write(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Validate claims-world CSVs against the contract.")
    p.add_argument("--in", dest="in_dir", type=Path, default=Path(".local/claims_world"))
    p.add_argument("--out", type=Path, default=Path(".local/validated"))
    a = p.parse_args()
    report = validate_dir(a.in_dir, a.out)
    for table, e in report["tables"].items():
        print(f"{table:10} {e['status']:8} raw={e['raw_rows']} valid={e['valid_rows']} "
              f"quarantined={e['quarantined_rows']} reconciles={e['reconciles']}")


if __name__ == "__main__":
    main()