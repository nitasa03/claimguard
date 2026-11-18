# Planted fraud rings (issue #10)

Planted rings give scenario S2 a known answer key. Config: `data/generators/config/rings_v1.yaml`.
Code: `data/generators/rings.py`. Tests: `tests/test_rings.py`.

## How to run
```
python -m data.generators.claims_world --rings data/generators/config/rings_v1.yaml
```
Tables go to `.local/claims_world/`; truth goes to `.local/claims_world_truth/`.

## What is planted (config v1.0.0, seed 42)
| Type | Shape | Links | Rings (size 3 / 5 / 10) | Claims |
|---|---|---|---|---|
| staged_collision | clique | shared tow, repair shop, clinic | 40 / 25 / 12 | 365 |
| shared_identity | bipartite | shared phone or address | 30 / 20 / 8 | 270 |

Total: 135 rings, 635 claims (0.6 percent). Each ring has one claim per claimant, inside a
time window (90 or 180 days). No claim or claimant is in two rings.

Decoys (honest, look suspicious): one tow vendor with 10 times the average claim count, and
50 households of 2 to 4 claimants sharing an address.

## Rules
- Existing claims are modified in place; contract v1 tables and columns are unchanged.
- The truth is used only for evaluation, never as a feature (label leakage).
- `fraud_label` is the observed outcome (investigated claims only); planted truth is complete.
  Investigated ring claims are labeled fraud at 80 percent.
- Ring randomness uses seed + 1000, so the base data is unchanged by ring settings.

## Truth files
- `planted_rings.csv`: ring_id, ring_type, shape, ring_size, claim_id, claimant_id, link_type, link_id (one row per link)
- `planted_decoys.csv`: decoy_id, decoy_type, claim_id, claimant_id, link_type, link_id
- `manifest.json`: config version, contract, seeds and counts (lineage)

## Assumptions
Ring counts are design assumptions chosen for stable evaluation per size (AT-S2-1) under the
prevalence cap; they are not measured real-world prevalence.