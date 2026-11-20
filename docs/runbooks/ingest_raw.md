# Runbook: load files into the raw zone

Issue #12. Code: `data/ingestion/ingest_raw.py`. Rules: `docs/data/raw_zone_convention.md`.

## What it does
- Uploads every `.csv` in one folder (not subfolders) to
  `claims_batch/source=<source>/ingest_date=YYYY-MM-DD/<dataset>_<yyyymmdd>_<seq>.csv`.
- Writes one manifest per load to `_manifests/source=<source>/ingest_date=YYYY-MM-DD/`.
- Rerun safe: a file with the same SHA-256 already in raw is skipped. Changed content
  gets the next sequence number. Uploads are create-only (`if_generation_match=0`).
- Planted ring truth is never ingested; it lives in its own folder for evaluation only.

## Identity (rule 7: only pipeline identities write)
The pipeline writes as a dedicated service account with no key file. A person
impersonates it with their own sign-in. The service account can create and read
objects in the raw bucket only; it cannot delete or overwrite.

One-time setup in Cloud Shell. Real names stay in the shell, never in the repo.

```bash
PROJECT=<project-id>
BUCKET=<raw-bucket-name>
SA=claimguard-ingest@$PROJECT.iam.gserviceaccount.com
gcloud config set project "$PROJECT"
gcloud services enable iamcredentials.googleapis.com
gcloud iam service-accounts create claimguard-ingest \
  --display-name="ClaimGuard raw ingestion (no keys)"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member="serviceAccount:$SA" --role=roles/storage.objectCreator
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member="serviceAccount:$SA" --role=roles/storage.objectViewer
gcloud iam service-accounts add-iam-policy-binding "$SA" \
  --member="user:$(gcloud config get account)" --role=roles/iam.serviceAccountTokenCreator
```
Permission changes can take a few minutes to apply.

## Run (Cloud Shell)
```bash
git clone https://github.com/nitasa03/claimguard && cd claimguard
python3 -m venv .venv && . .venv/bin/activate && pip install -q -e .
python -m data.generators.claims_world --rings data/generators/config/rings_v1.yaml
export CLAIMGUARD_RAW_BUCKET="$BUCKET" CLAIMGUARD_INGEST_SA="$SA"
python -m data.ingestion.ingest_raw --in .local/claims_world --dry-run
python -m data.ingestion.ingest_raw --in .local/claims_world
python -m data.ingestion.ingest_raw --in .local/claims_world   # rerun: 0 uploaded
```

## Check
```bash
gcloud storage ls -r "gs://$BUCKET/claims_batch/"
gcloud storage cat "gs://$BUCKET/_manifests/source=synthetic/ingest_date=*/load_*.json"
# least privilege: the service account must not be able to delete (expect 403)
gcloud storage rm "gs://$BUCKET/claims_batch/source=synthetic/ingest_date=<date>/vendors_<yyyymmdd>_001.csv" \
  --impersonate-service-account="$SA"
```

## Offline (no cloud)
```bash
python -m data.ingestion.ingest_raw --in .local/claims_world --local-root .local/fake_bucket
```
