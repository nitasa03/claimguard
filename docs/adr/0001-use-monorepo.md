# ADR-0001: Use a single monorepo for ClaimGuard

- Status: Accepted
- Date: 2026-11-09
- Deciders: Nibedita Satapathy

## Context
ClaimGuard has data pipelines, ML code, agents, services, infrastructure and
documentation. One person builds it, in a browser-based development
environment with limited free hours. Many changes cut across components: a
column change touches the data contract, the transform, the tests and the docs.

## Decision
Keep all components in one GitHub repository, with one top-level folder per
area (infra, data, ml, agents, services, ui, evals, docs, tests) and shared
tooling at the root. One dev container serves the whole repository. Once CI
exists, path filters make each area run only its own checks.

## Alternatives considered
- One repository per component: stronger isolation and independent releases,
  but more overhead for one person, and cross-component changes need several
  coordinated pull requests.
- A separate repository for documentation: documents drift away from the code
  they describe.
- Data files in the repository: rejected because of size and dataset licenses.
  Data lives in cloud storage; only tiny samples are committed.

## Consequences
+ One pull request can change code, tests and docs together.
+ One CI configuration, one dev container, one issue tracker.
- The repository will grow, and CI must stay fast. Path filters help.
- There are no ownership boundaries between components. Code owners can add them later.

## Revisit when
CI regularly takes over 10 minutes, a component needs its own release
schedule or different access control, or more than one person works on it.
