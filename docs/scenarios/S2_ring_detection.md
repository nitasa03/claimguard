# S2 — Staged-collision ring detection

## Problem
Organized rings stage collisions and file several claims that look normal one at a time.
The fraud only shows in the links between claims: shared tow operators, repair shops,
clinics, phones or addresses.

## Users
Special investigations unit (SIU) investigator; claims reviewer handling a flagged case.

## Trigger
Nightly graph build, and on demand when a case is opened.

## Inputs
Silver tables: claims, claimants, vehicles, vendors (tow, shop, clinic), addresses, phones.

## Outputs
Ring evidence per case: cluster ID, member claims, linking entities with type,
ring score, and match confidence for each resolved entity.

## Data
D2 synthetic claims world with planted rings (#10). Planted-truth table is kept
separate and used only for evaluation. No real personal data.

## Method
1. Entity resolution: normalize names, addresses and phones; match with rules plus
   fuzzy similarity; keep a confidence per match.
2. Graph build: claims linked to resolved entities; only events known before the
   scoring time are used.
3. Clustering: connected components, then community detection on large components.
4. Ring scoring: shared vendors, claims close together in time, repeated participants.
5. Evidence: every link lists the entity that creates it.

## Metric
Ring precision and recall against planted truth, reported at ring sizes 3, 5 and 10.
Entity-resolution precision and recall on a labeled sample.

## Failure modes
- Hub entities (a busy tow company or body shop) link unrelated claims.
- Over-merging similar names creates false links; under-merging hides real ones.
- Legitimate shared addresses (families, apartment buildings) look like rings.
- Very large components hide small rings.
- Using claims filed after the scoring time leaks future information.

## Human decision
The investigator decides whether the links are meaningful. The system never refers
or denies a claim on ring evidence alone.

## Acceptance tests
- AT-S2-1: Precision and recall reported against planted truth at ring sizes 3, 5 and 10.
- AT-S2-2: Every flagged link names its linking entity and entity type.
- AT-S2-3: Ambiguous entity matches carry a confidence score.
- AT-S2-4: Components above the size cap are flagged and not scored as one ring.
- AT-S2-5: Hub entities above a degree threshold are down-weighted; a test with one
  planted hub shows no false ring.
- AT-S2-6: The same seed and data produce the same clusters.
- AT-S2-7: Leakage test: no edge uses a claim dated after the scoring time.
