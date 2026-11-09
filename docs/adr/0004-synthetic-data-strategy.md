# ADR-0004: Generate synthetic data with planted ground truth

- Status: Accepted
- Date: 2026-11-09
- Deciders: Nibedita Satapathy

## Context
ClaimGuard needs claims, policies, vendors, documents, photos and events that
resemble an insurer's data, with known fraud patterns so detection can be
measured. Real insurer data is not available and must not be used. Public
datasets exist, but they are small, mostly tabular, differ in license and
provenance, and contain no vendor networks, documents or investigation
workflow. Evaluation needs ground truth: which claims belong to which planted
pattern.

## Decision
Build a seeded, parameterized generator in Python that produces:
- Linked entities: policies, claimants, vehicles, claims, payments, vendors
  (tow, repair, clinic, rental), addresses and phone numbers.
- Planted typologies, such as staged-collision rings that share vendors,
  contact details or timing, plus single-claim patterns such as claims shortly
  after policy start.
- Documents rendered from templates (invoices, estimates, forms) and degraded
  to look scanned, and event streams, with realistic mess: typos, duplicates,
  missing fields, late records and schema changes.
- Two separate label sets: planted truth, used only for evaluation, and
  observed labels that mimic investigation (only some claims are examined, and
  results arrive late).

Public datasets inform realistic distributions only, within their licenses.
They are not copied into the repository or redistributed.

## Alternatives considered
- A public claims dataset alone: no networks, documents or workflow, and
  provenance and license vary.
- Existing research simulators for insurance-fraud networks: useful as design
  references and cited in the related-work page. They are not reused as the
  data source without a license and fit check.
- LLM-generated records: hard to control, inconsistent across tables, and no
  reliable ground truth.
- Models that learn from real data to synthesize more: needs real data, which
  is unavailable.

## Consequences
+ Exact ground truth, reproducible runs (fixed seed and configuration), no
  privacy risk, and scenarios can be varied on demand.
+ Volume can be scaled up to practise partitioning and cost control.
- Results show that the pipeline and agents work, not that they would perform
  on a real insurer's claims. This limit is stated in every report and data card.
- A model can learn the generator's quirks. Mitigation: vary parameters across
  runs, add noise, and hold out generator configurations for testing.
- Building the generator takes time and must itself be tested.

## Controls
- Every dataset has a data card: source, what is real or synthetic, parameters,
  seed, generator version and known limits.
- The generator version and seed are recorded in each load's manifest.
- No real names, businesses or identifiers are used; vendor names are invented.

## Revisit when
Real or licensed data becomes available, a reviewer shows the generator is
unrealistic for a target scenario, or an open synthetic dataset with planted
networks is found that fits better.

## References
- Raw zone convention (docs/data/raw_zone_convention.md)
- Related-work page (docs/related_work.md, to be added)
- ADR-0003: development region
