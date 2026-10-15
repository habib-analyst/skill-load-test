# skill-load-test audit: clinic

Router: `tfidf` | distractor strategy: `franchise` (seed 7) | tau=0.2833 (frozen, calibrated at N=4) | shortlist top-3, max 3 loads

## Load reliability vs catalog size

| catalog size | recall@1 | recall@3 | recall@10 | loaded | zero-load | mean loads |
|---|---|---|---|---|---|---|
| 4 | 1.000 | 1.000 | 1.000 | 0.750 | 0.250 | 0.75 |
| 20 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.25 |
| 100 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 2.00 |

recall@10 is the explicit-selection analog: is the needed skill recognizable inside a compact candidate set. `loaded` applies the implicit-load rule (score >= tau, top-3 shortlist).

## Failure-mode taxonomy (largest catalog, N=100)

| mode | tasks | meaning |
|---|---|---|
| ok | 4 | golden skill loaded |
| outranked | 0 | golden in top-10 but outside the top-3 shortlist: semantic interference from distractor descriptions |
| skipped | 0 | golden in top-3 but below the frozen tau: score deflation under interference |
| buried | 0 | golden beyond top-10 |

## Per-skill outcome at N=100

| skill | rank | score | loaded | taxonomy | gap at smallest |
|---|---|---|---|---|---|
| find-doctor | 1 | 0.3229 | yes | ok | yes (pre-existing) |
| book-appointment | 1 | 0.3423 | yes | ok | no |
| reschedule-appointment | 1 | 0.6029 | yes | ok | no |
| cancel-appointment | 1 | 0.3554 | yes | ok | no |

_gap at smallest = misses even at the smallest catalog: a metadata/description gap, not a scale effect. Fix the skill description, not the router._
