# Data source register

Status: draft v0.2, updated 2026-11-09.

For each data source ClaimGuard might use: what it is, its terms, and the
decision. Summaries are my reading of public pages, not legal advice; the terms
published by each source prevail.

## Summary

| ID | Source | Used for | Terms status | Decision |
|---|---|---|---|---|
| S01 | Synthetic generator (own work) | Core data | Own work | Use |
| S02 | Kaggle vehicle claim fraud dataset | Feature-range reference, baseline experiments | Verified 2026-11-09 (CC0, uploader's declaration) | Use; not committed to the repository |
| S03 | Toronto Police traffic collision data | Realistic timing, place and severity patterns | Checked 2026-11-09 | Use, with attribution |
| S04 | CarDD car-damage images | Damage-detector experiments (stretch) | Partly checked | Deferred: verify before Sprint 3 |
| S05 | FUNSD scanned forms | OCR robustness tests | To verify | Deferred: verify before Sprint 3 |
| S06 | SROIE scanned receipts | OCR robustness tests | To verify | Deferred: verify before Sprint 3 |
| S07 | CORD receipts | OCR robustness tests | To verify | Deferred: verify before Sprint 3 |
| S08 | NHTSA vPIC API | VIN decoding | Checked 2026-11-09 | Use |
| S09 | Open-Meteo API | Weather on the loss date | Checked 2026-11-09 | Use, with attribution |
| S10 | Mock vehicle-history service (own work) | Vendor enrichment | Own work | Build |
| S11 | LLM-written notes and emails | Synthetic text | Provider terms apply | Use; label as synthetic |

## Rules
1. A source is loaded only after its terms are recorded here with a decision.
2. If the license cannot be found or does not allow the use, the decision is Skip.
3. No third-party dataset is committed to this repository or redistributed.
4. Every load records the source ID, license note and check date in its manifest.
5. Required attributions appear in the data card and wherever the data is shown.

## Details

### S01 Synthetic generator
- What: seeded generator for claims, entities, documents and events (ADR-0004).
- Terms link: not applicable (own work).
- Redistribution: repository content is all rights reserved.

### S02 Kaggle vehicle claim fraud dataset
- What: a public vehicle insurance claims table with a fraud label (FraudFound_P)
  covering vehicle, accident and policy details.
- Terms link: https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection
- License shown on the page: CC0 1.0 Universal (public domain dedication),
  declared by the uploader. Checked 2026-11-09.
- Provenance on the data card: source "Oracle Databases", collected by web
  download, no citation. The upstream owner's terms are not stated.
- Caveat: CC0 is the uploader's declaration; Creative Commons states it has not
  verified the copyright status of works it is applied to.
- Allowed here: private use only, as a reference for feature ranges and baseline
  experiments. It is not a core dependency.
- Redistribution: no. Not committed to this repository; not republished.
- Stored: private raw bucket, source=public_kaggle_vehicle_claim_fraud, with the
  license and provenance notes in the manifest.
- Limit: not representative of real Canadian claims; stated in every report.
- Revisit when: an upstream license is found, or before any result is presented as
  a benchmark.

### S03 Toronto Police traffic collision data
- What: open data on traffic collisions from the Toronto Police Service and the
  City of Toronto Open Data site.
- Terms link: https://www.tps.ca/data-maps/resources/licence/
- Terms: Open Government Licence - Ontario: a worldwide, royalty-free, perpetual,
  non-exclusive licence to use the information, including commercially, subject
  to its terms. Read the attribution statement and exemptions before use.
- Allowed here: calibrate collision times, places and severity in synthetic data.
- Redistribution: only as the licence permits; the repository holds no raw files.
- Attribution: required; copy the statement from the licence page into the data card.

### S04 CarDD car-damage images
- What: car-damage images with annotations.
- Terms link: to add after checking the official page.
- Terms (partly checked): non-commercial research and education use; access
  requires agreeing to the terms of the image sources. A third-party copy lists a
  different license, so follow the original authors' terms.
- Redistribution: no. Never committed.
- Decision: deferred until verified.

### S05 FUNSD, S06 SROIE, S07 CORD
- What: public document-understanding datasets (scanned forms and receipts), used
  only to test OCR on noisy scans.
- Terms link: to add after checking each official page.
- Redistribution: no.
- Decision: deferred until verified.

### S08 NHTSA vPIC API
- What: a free US government service to decode VINs.
- Terms link: https://vpic.nhtsa.dot.gov/api/home/index/faq (free public use, no
  registration).
- Limits: covers US-market vehicle data; no accident or title history.
- Redistribution: raw responses are stored in the raw zone, not committed.

### S09 Open-Meteo API
- What: a weather API.
- Terms link: https://open-meteo.com/en/terms
- Terms: free for non-commercial use; data under CC BY 4.0; fair-use limits
  (under 10,000 calls a day).
- Attribution: "Weather data by Open-Meteo.com" with a link, wherever shown.
- Redistribution: shared data needs attribution; the repository holds none.

### S10 Mock vehicle-history service
- What: a small service I build, because no free vehicle-history source exists.
- Terms link: not applicable (own work). Data is invented.

### S11 LLM-written notes and emails
- What: synthetic claim notes generated with an LLM.
- Terms link: the model provider's terms page, to add before large runs.
- Redistribution: outputs are synthetic; confirm the provider's terms.
- Marked source_type=synthetic.
