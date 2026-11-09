# Raw zone convention

Status: draft v0.1. Applies to the raw (bronze) Cloud Storage bucket.

## Purpose
The raw zone keeps every file exactly as received. Nothing is edited or
renamed. Validation, silver and gold tables can always be rebuilt from it.

## Bucket
- One private raw bucket per environment. Name pattern:
  claimguard-raw-<env>-<random suffix>. Real names live in configuration,
  not in this repository.
- Region per ADR-0003. Standard storage class.
- Uniform bucket-level access; public access prevention enforced.
- Object versioning on, limited to 2 versions per object; noncurrent versions
  expire after 7 days.
- No retention lock while the system is being tested.

## Layout
gs://<raw-bucket>/<domain>/source=<source>/ingest_date=YYYY-MM-DD/<file>

| Domain | Contents | Format |
|---|---|---|
| claims_batch | Batch extracts of claims, policies, payments | CSV |
| claim_events | Event streams, with an hour=HH level | JSON lines |
| cdc | Change feeds from operational databases | JSON or Parquet |
| documents | Invoices, estimates and forms, grouped by claim_id | PDF, TIFF |
| images | Photos | JPG, PNG |
| vendor_feeds | Raw API responses | JSON |
| _manifests | One manifest per load | JSON |
| _test | Throwaway test objects, deleted after use | any |

Source values: synthetic, public_<dataset name>, api_<service name>.

## File naming
- Lowercase, no spaces: <dataset>_<yyyymmdd>_<sequence>.<ext>
- The original file name is stored in the manifest.
- A re-delivery gets a new sequence number. Files are never overwritten.

## Rules
1. Write once. Corrections arrive as new files, never edits.
2. Every load has a manifest with: file name, source, source_type
   (synthetic or public), size, SHA-256 checksum, row count for tabular files,
   ingest time, license note and load id.
3. Only synthetic and public data are stored. No real personal information.
4. Public datasets are stored only where their license allows it, and are never
   redistributed. The license note is recorded in the manifest and in the
   source register.
5. Partition by ingest date, not by the date of the event inside the data.
6. Rejected files are copied to a separate quarantine location with the
   reason; the raw copy is left untouched.
7. Only pipeline identities write to the bucket. People have read access.
   Permissions follow least privilege.

## Examples
| Type | Path |
|---|---|
| Nightly claims extract | claims_batch/source=synthetic/ingest_date=2026-11-10/claims_20261110_001.csv |
| Event batch | claim_events/source=synthetic/ingest_date=2026-11-10/hour=14/events_20261110_001.jsonl.gz |
| Invoice | documents/source=synthetic/ingest_date=2026-11-10/claim_id=C000123/invoice_20261110_001.pdf |
| API response | vendor_feeds/source=api_vin_decode/ingest_date=2026-11-10/response_20261110_001.json |

## Related
- ADR-0003: development region
- Source register (docs/data/source_register.md, to be added)
