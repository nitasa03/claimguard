# Sprint 0 review

Dates: 4 to 9 November 2026 (planned end: 8 November).

## Sprint goal
Set up a secure public repository, project skeleton, cloud project and storage,
and the first decisions and documents.

## Result
Setup and decisions were delivered. One documentation issue was carried over
and one was split.

| Issue | Points | Result |
|---|---|---|
| #1 Repository setup, security, skeleton | 8 | Done |
| #2 Cloud project, budget alerts, region | 3 | Done |
| #3 Raw storage bucket and convention | 2 | Done |
| #4 Data source register | 3 | Done |
| #5 Scenario specs | 5 | Split: S1 done (2); S2 and S3 moved to Sprint 1 (3) |
| #6 Architecture decision records | 3 | Done (ADR-0001 to ADR-0004) |
| #7 Sanitized master plan | 2 | Carried to Sprint 1 |
| #8 Related-work page | 2 | Done |

Planned: 28 points. Completed: 23. Carried over: 5.

Velocity: 23 points in the first sprint. Treat it as an upper bound: issue #1
(8 points) bundled a lot of one-off security setup.

## Delivered
- Public repository with a security policy, branch protection, dependency and
  secret scanning, and a read-only workflow token.
- Folder skeleton and starter documents, with a data source register and a
  raw-zone convention.
- A cloud project with budget alerts, a private versioned storage bucket and a
  tested upload and delete.
- ADR-0001 monorepo, ADR-0002 BigQuery, ADR-0003 development region,
  ADR-0004 synthetic data strategy.
- Related-work page and the S1 scenario spec.

## Decisions changed during the sprint
- Development region: a US free-tier region instead of a Canadian one (ADR-0003).

## What went well
- Security settings were in place before any code was written.
- Licenses were checked before data was used.
- Decisions were written down with alternatives and revisit triggers.

## What did not go well
- Several issues were closed with criteria still open, then reopened.
- The scope of the document work was underestimated.
- One issue was too large and had to be split at review.

## Lessons
- Assign the milestone and owner when an issue is created.
- Close an issue only when every acceptance criterion is met.
- Check the cloud billing state before planning cloud work.
- Check a dataset's provenance, not only its license label.
- Split large issues at planning, and record any split openly.

## Risks carried forward
- Free-tier allowances can change; usage is checked against billing reports.
- OCR dataset licenses are unverified; those sources stay blocked until checked.
- Budget alert delivery will be confirmed by the first real alert.

## Next: Sprint 1 (9 to 22 November)
Goal: data foundation: generator, raw landing, validation, quarantine, silver
tables and CI. Carried in: #7 (sanitized master plan) and the S2 and S3 specs.
