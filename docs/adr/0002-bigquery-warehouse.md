# ADR-0002: Use BigQuery as the analytical warehouse

- Status: Accepted
- Date: 2026-11-09
- Deciders: Nibedita Satapathy

## Context
The silver and gold layers need typed, queryable tables for validation results,
features, graph edges and agent case views. Workloads are analytical: scans and
aggregations over a few columns of many rows, not frequent single-row updates.
There is no operations team, so the warehouse should need no servers to run.
Cost must stay minimal.

## Decision
Use BigQuery in the development region chosen in ADR-0003. Transform with SQL
(dbt models and tests). Keep raw files in Cloud Storage as the permanent
record, so the warehouse can always be rebuilt from them.

## Alternatives considered
- Cloud SQL (PostgreSQL): a row-oriented transactional database. It suits
  application state, but analytical scans are slower, and a running instance
  bills by the hour even when idle.
- DuckDB: free and excellent for local development and tests. It is used for
  that purpose, but it is not a shared, managed warehouse.
- Snowflake, Redshift or Databricks SQL: strong platforms, but they add cost or
  trial limits and more setup. Databricks and Delta Lake may be explored later
  as a separate exercise.

## Consequences
+ Serverless: no cluster to size, patch or turn off.
+ Columnar storage: queries read only the columns they use.
+ A free monthly allowance (see Google's pricing page) fits the project's size.
+ Native integration with Cloud Storage, Cloud Run, IAM and dbt.
- Queries are billed by data scanned, so cost depends on query discipline.
- A dataset's location is fixed when it is created.
- Some vendor lock-in. SQL and dbt models stay portable, and raw data stays in
  open file formats.

## Cost controls
- Partition large tables by ingest date and require a partition filter.
- Cluster on commonly filtered keys; select only the needed columns.
- Set a maximum bytes billed on queries and a project query quota.
- Use short default table expiry for scratch datasets.
- Review billing reports before and after each cloud session.
- Track actual bytes scanned and storage in the billing reports each sprint.

## Revisit when
Queries regularly exceed the free allowance, row-level transactions are
needed, or a different platform becomes the working standard for the target
roles.

## References
- BigQuery pricing and free-tier documentation
- ADR-0003: development region
