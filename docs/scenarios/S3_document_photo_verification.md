# S3 — Document and photo verification

## Problem
Inflated or altered invoices, estimates and bills, and reused damage photos,
add cost to claims. Checking each document by hand is slow and inconsistent.

## Users
Claims reviewer; SIU investigator.

## Trigger
A document or photo is uploaded to a claim.

## Inputs
PDFs and scans (FNOL forms, estimates, repair invoices, tow and clinic bills) and
damage photos, plus the claim record from silver tables.

## Outputs
Extracted fields with confidence, validation results, inconsistency flags,
and duplicate matches (invoice numbers, images).

## Data
- D5 synthetic documents, degraded into scan-like copies, with planted tampering.
- CarDD damage photos with planted duplicates (source register S04; images are
  never committed to this repo).
- FUNSD, SROIE and CORD scanned forms and receipts, for OCR robustness tests only
  (source register S05 to S07).
  S04 to S07 are blocked until their terms are verified and recorded in the source register.

## Method
1. OCR, then schema-based extraction of fields per document template.
2. Validation rules: totals add up, VIN format, date order, required fields present.
3. Cross-check extracted fields against the claim (dates, VIN, amounts, vendor).
4. Duplicate checks: repeated invoice numbers; reused images by perceptual hash,
   including resized or cropped copies.

## Metric
Field accuracy per template and per scan quality (clean, mild, heavy);
planted tampering detection rate; duplicate detection rate; review-queue rate.

## Failure modes
- Poor scans give wrong values with high confidence.
- New or unknown templates are extracted badly.
- Cropped, rotated or recolored photos escape duplicate checks.
- Legitimate repeats (a vendor reissuing a corrected invoice) are flagged.
- A cross-check fails because the claim record itself is wrong.

## Human decision
The reviewer decides how to treat flagged inconsistencies. The system flags and
explains; it does not reject a document.

## Acceptance tests
- AT-S3-1: Field accuracy reported per template and scan quality.
- AT-S3-2: Planted tampering detected at a stated rate.
- AT-S3-3: Planted duplicate invoices and images (including resized and cropped)
  detected at a stated rate.
- AT-S3-4: Fields below the confidence threshold go to the review queue; queue rate reported.
- AT-S3-5: Unreadable files produce a re-upload request, not a silent failure.
- AT-S3-6: A repo check confirms no CarDD or other licensed images are committed.
