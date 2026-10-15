# skill-load-test audit: hostel-ops

Router: `tfidf` | distractor strategy: `franchise` (seed 7) | tau=0.1518 (frozen, calibrated at N=14) | shortlist top-3, max 3 loads

## Load reliability vs catalog size

| catalog size | recall@1 | recall@3 | recall@10 | loaded | zero-load | mean loads |
|---|---|---|---|---|---|---|
| 14 | 0.857 | 0.929 | 1.000 | 0.786 | 0.143 | 1.21 |
| 50 | 0.786 | 0.786 | 0.857 | 0.786 | 0.143 | 1.43 |
| 200 | 0.786 | 0.857 | 0.857 | 0.786 | 0.143 | 1.36 |

recall@10 is the explicit-selection analog: is the needed skill recognizable inside a compact candidate set. `loaded` applies the implicit-load rule (score >= tau, top-3 shortlist).

## Failure-mode taxonomy (largest catalog, N=200)

| mode | tasks | meaning |
|---|---|---|
| ok | 11 | golden skill loaded |
| outranked | 0 | golden in top-10 but outside the top-3 shortlist: semantic interference from distractor descriptions |
| skipped | 1 | golden in top-3 but below the frozen tau: score deflation under interference |
| buried | 2 | golden beyond top-10 |

## Per-skill outcome at N=200

| skill | rank | score | loaded | taxonomy | gap at smallest |
|---|---|---|---|---|---|
| greeting | 72 | 0.0134 | no | buried | yes (pre-existing) |
| check-availability | 2 | 0.1333 | no | skipped | yes (pre-existing) |
| book-room | 1 | 0.3139 | yes | ok | no |
| cancel-booking | 1 | 0.1652 | yes | ok | no |
| modify-booking | 1 | 0.2126 | yes | ok | no |
| check-in | 1 | 0.2191 | yes | ok | no |
| check-out | 1 | 0.2681 | yes | ok | no |
| late-checkout | 1 | 0.3464 | yes | ok | no |
| housekeeping | 1 | 0.2694 | yes | ok | no |
| payment-info | 33 | 0.0000 | no | buried | yes (pre-existing) |
| complaint | 1 | 0.2131 | yes | ok | no |
| review | 1 | 0.1809 | yes | ok | no |
| owner-digest | 1 | 0.4509 | yes | ok | no |
| owner-approve | 1 | 0.4615 | yes | ok | no |

_gap at smallest = misses even at the smallest catalog: a metadata/description gap, not a scale effect. Fix the skill description, not the router._
