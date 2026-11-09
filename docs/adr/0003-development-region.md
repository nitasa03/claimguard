# ADR-0003: Use a US free-tier region for development

- Status: Accepted
- Date: 2026-11-09
- Deciders: Nibedita Satapathy
- Supersedes: the earlier plan to develop in a Canadian region

## Context
ClaimGuard uses only synthetic and public data, and development cost should
stay minimal. Google Cloud's always-free Cloud Storage allowance, at the time
of writing, covers Standard storage in us-central1, us-east1 and us-west1.

Public guidance suggests no single Canadian statute imposes a general
data-residency requirement, but regulated insurers are expected to control
where production customer data sits and who can access it (OSFI third-party
risk guidance, PIPEDA, Quebec Law 25). Non-production environments that hold
only synthetic data are a lower-risk case.

## Decision
Run development in us-central1: the raw bucket, BigQuery datasets and Cloud Run
services all use the same region. Region, project and bucket names are kept in
configuration, never hard-coded, so they can change.

## Alternatives considered
- Toronto or Montreal: matches production expectations, costs slightly more.
- Mixed regions: rejected. BigQuery loads need a dataset and bucket in
  compatible locations, and transfers between locations add cost and complexity.

## Consequences
+ Lowest cost; some usage may fall inside the free allowance.
+ One region everywhere keeps loads, jobs and services simple.
- The running system does not demonstrate Canadian data residency.
- A bucket's or dataset's location cannot be changed in place. Moving to a
  Canadian region later means creating new resources there and copying or
  reloading the data.

## Data classification
Only synthetic and public data are stored. No real personal information is
used in any environment of this project.

## Production position
A production deployment holding real customer data would run in a Canadian
region, after a privacy impact assessment, with contractual safeguards and
reviewed access controls. Residency is not sovereignty: a US provider's
Canadian region can still be subject to US law.

## Revisit when
Any real or restricted data is involved, the free-tier terms change, or a
needed service is unavailable in us-central1.

## References
- Google Cloud Storage pricing and Always Free limits
- OSFI Guideline B-10, Third-Party Risk Management
- PIPEDA and Quebec Law 25 (cross-border transfers)
