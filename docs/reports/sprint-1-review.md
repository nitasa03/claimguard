# Sprint 1 review

Dates: 9 to 22 November 2026 (review held 27 November).

## Sprint goal
Build the data foundation: generator, raw landing, validation, quarantine,
silver tables and CI.

## Plan versus actual
The foundation was delivered except the silver tables, which moved to Sprint 2
at re-planning. The stretch item was not started.

| Issue | Result |
|---|---|
| #17 Scenario specs S2 and S3 | Done |
| #9 Synthetic data generator v1 | Done |
| #10 Plant ring typology | Done |
| #11 Data contract | Done |
| #15 CI on pull requests | Done |
| #13 Validation and quarantine | Done |
| #12 Ingestion to raw | Done (follow-up fix merged 23 November) |
| #16 Sprint 1 review | Closed by this report, 5 days late |
| #14 Silver tables | Moved to Sprint 2 during the sprint (5 points) |
| #7 Sanitized master plan (stretch) | Not done; moved to Sprint 2 |

| Measure | Points |
|---|---|
| Initial plan | 32 |
| Re-planned commitment (after #14 moved) | 27 |
| Completed by sprint end | 25 |
| Open at sprint end | 2 (#16) |

Velocity: 25 points, against 23 in Sprint 0.

## Delivered
- Seeded synthetic claims world: 100,000 claims, 108,201 payments, 60,000
  policies, claimants and vehicles, and 1,000 vendors.
- 135 planted fraud rings (635 ring claims) and 1,535 decoy rows, defined in a
  config file. Ground truth is kept apart and never ingested.
- Data contract v1.0.1 with file-level checks.
- Row-level validation with quarantine reasons and reconciliation.
- Raw-zone ingestion: checks before upload, SHA-256 dedupe, create-only
  uploads, a manifest per load, and a first load to the cloud raw bucket
  through a service identity with no keys.
- CI on every pull request (lint and tests) as a required check; 95 tests on
  main.
- Scenario specs S2 and S3.

## Lesson learned
Hold the sprint review on the sprint's last day. A late review leaves the
milestone open and blurs where the next sprint starts.

## Next: Sprint 2 (23 November to 6 December, 21 points)
Goal: ring detection end to end, from raw files to rings scored against the
planted truth, run by one pipeline.
Issues: #14 silver tables, #23 ring graph, #24 ring detection, #25
orchestration, #26 repository quality gates, #27 Sprint 2 review. Carried in:
#7 (sanitized master plan).
