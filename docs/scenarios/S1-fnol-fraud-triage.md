# S1: FNOL fraud triage (single claim)

Status: draft v0.1, 2026-11-09. Synthetic and public data only.

## Problem
Investigators cannot review every claim. At first notice of loss (FNOL), a
claim needs a fast, explainable decision about where it goes next, using only
what is known at that moment.

## Users
- SIU investigator: receives referred claims.
- Claims adjuster: handles fast-tracked and reviewed claims.

## Decision supported
Route each new claim to one of: fast-track, standard review, or referral to
the investigation team. A person decides on any adverse action.

## Trigger and flow
1. A new-claim event arrives after FNOL.
2. Features are computed as known at that time (point in time).
3. The model returns a fraud score; rules add flags.
4. The top reasons for the score are attached.
5. A threshold tied to investigator capacity sets the route.
6. The result is stored with the model and feature versions.

## Inputs
| Input | Source | Known at FNOL |
|---|---|---|
| Claim facts (type, amount, loss date, report time) | claims table | Yes |
| Policy dates and coverage | policy table | Yes |
| Claimant history (earlier claims, tenure) | claimant tables | Yes |
| Vehicle details | VIN decode, claim form | Yes |
| Weather on the loss date | weather API | Yes |
| Investigation outcome, payments, adjuster notes | later systems | No: never used as features |

## Outputs
Fraud score, top reasons, route, degraded-mode flag, versions used.

## Data
Synthetic claims world (ADR-0004). The public Kaggle claims table is used only
as a private reference for feature ranges (source register S02).

## Method
- Rules baseline: simple flags such as a claim soon after policy start.
- Gradient-boosted model (LightGBM or XGBoost) with SHAP reasons.
- Cost-aware threshold set from investigator capacity.
- Protected characteristics and close proxies are not used; proxies are
  reviewed and documented.

## Metrics
- Primary: PR-AUC on a time-based split; precision and recall at investigator
  capacity (top k claims per week).
- Also: calibration, stability of reasons, comparison with the rules baseline.
- Targets are set after the first baseline run, not before.

## Failure modes and fallbacks
| Failure | Response |
|---|---|
| Missing fields | Flag the claim and request more information |
| Weather or VIN service down | Score without it and mark degraded |
| Model unavailable | Rules-only score, marked degraded |
| Label delay or bias (only investigated claims have labels) | Report observed and planted-truth metrics separately |
| Drift in inputs or scores | Monitor and raise an alert |

## Human decision
A person decides any referral outcome or adverse action. The system only
recommends a route.

## Acceptance tests
1. Evaluated on a time-based split, never a random split.
2. A leakage test shows every feature was known at FNOL.
3. Every score returns its top reasons.
4. A forced service failure produces a degraded-mode flag.
5. The number of referrals never exceeds the configured capacity.
6. PR-AUC and precision and recall at capacity are reported against the baseline.

## Out of scope
Automatic denial, payment or cancellation; real customer data.

## Related
ADR-0004 (synthetic data), docs/data/source_register.md
