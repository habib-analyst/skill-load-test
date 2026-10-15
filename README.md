# skill-load-test

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![GitHub stars](https://img.shields.io/github/stars/habib-analyst/skill-load-test.svg)](https://github.com/habib-analyst/skill-load-test)

**The open harness that measures whether agents load the right skills as the skill catalog grows.** A skill pack nobody's agent loads is dead weight. This tool audits any skill pack at configurable catalog sizes and reports per-skill load hit-rate, top-k retrieval quality, and a failure-mode taxonomy. Deterministic, CPU-only, zero dependencies.

## Quickstart

```bash
pip install skill-load-test

skill-load-test audit clinic.pack \
  --tasks clinic_tasks.jsonl \
  --catalog-sizes 4,20,100 \
  --distractor-packs hostel-ops.pack restaurant.pack
```

Real output (reference run, `examples/run_reference_audit.py`):

```
Router: `tfidf` | distractor strategy: `franchise` (seed 7) | tau=0.2833 (frozen, calibrated at N=4) | shortlist top-3, max 3 loads

| catalog size | recall@1 | recall@3 | recall@10 | loaded | zero-load | mean loads |
|---|---|---|---|---|---|---|
| 4 | 1.000 | 1.000 | 1.000 | 0.750 | 0.250 | 0.75 |
| 20 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 1.25 |
| 100 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 2.00 |

recall@3 4 -> 100: 1.000 -> 1.000 (drop 0.000)
```

`clinic.pack` (4 skills) is scale-robust: every skill still loads at N=100. Not every pack survives. See measured results.

## Measured results

Reference audits over packc example packs (TF-IDF router, franchise distractors, seed 7; reproduce with `examples/run_reference_audit.py`):

**hostel-ops** (14 skills, 14 tasks), catalog 14 / 50 / 200:

| catalog size | recall@1 | recall@3 | recall@10 | loaded | zero-load |
|---|---|---|---|---|---|
| 14 | 0.857 | 0.929 | 1.000 | 0.786 | 0.143 |
| 50 | 0.786 | 0.786 | 0.857 | 0.786 | 0.143 |
| 200 | 0.786 | 0.857 | 0.857 | 0.786 | 0.143 |

Failure-mode taxonomy at N=200: **11 ok, 1 skipped, 2 buried**. The two buried skills tell the story:

| skill | rank at N=14 | rank at N=200 | diagnosis |
|---|---|---|---|
| `greeting` | 1 | 72 | scale-buried: distractor descriptions sharing "guest/customer" crowd it out (semantic interference) |
| `payment-info` | 10 | 33 | metadata gap worsened by scale: description ("Share the property's payment methods.") shares almost no vocabulary with how users ask ("how do I pay") |

`check-availability` is the `skipped` case: rank 2 at N=200, but its score (0.133) falls below the frozen tau (0.152) calibrated at N=14. Score deflation under interference, the exact signature the motivating paper reports.

**Router comparison** (same hostel-ops audit, BM25 router): recall@3 stays 0.929 at all three scales; only `payment-info` stays buried. Lexical routing choice changes which fragile skills surface, which is why the harness ships both routers and reports both.

**clinic** (4 skills), catalog 4 / 20 / 100: recall@3 = 1.000 at every scale. Well-written descriptions survive scale.

27 tests, all green (`pytest tests/`). No network, no model calls, no mocks of the core measurement: the router ranks real skill metadata and the load rule is applied to real scores.

## How it works

```
tasks (utterance -> golden skills)      skill pack (name + description each)
        \                                        /
         \                                      /  + distractors (real packs
          v                                    v     or seeded franchise variants)
   ┌─────────────┐                   ┌─────────────────────┐
   │   router    │<── metadata only │ catalog at size N   │
   │ tfidf/bm25  │   (progressive   └─────────────────────┘
   └──────┬──────┘    disclosure)              grows: 14 -> 50 -> 200
          v
   ┌─────────────┐
   │ implicit-   │  load iff score >= tau (frozen, calibrated
   │ load rule   │  once at smallest N), top-3 shortlist
   └──────┬──────┘
          v
   per-skill hit-rate | recall@k | zero-load rate | taxonomy
   (ok / outranked / skipped / buried, plus pre-existing gap flag)
```

The design mirrors the experiment in "Lost in Implicit Routing" (arXiv 2610.18522): hold tasks and golden skills fixed, grow the catalog with irrelevant skills, and watch loading degrade. The difference: this harness is **model-agnostic**. It measures observed loads from a deterministic routing step instead of LLM internals, so any publisher can audit any pack on CPU in seconds. Catalog adapters cover `.pack` files, plain JSON catalogs, `packc publish` registries (`registry.json` -> tarballs), and Agent Skills channel directories of `SKILL.md` files.

## Limitations (honest)

- The routers are lexical (TF-IDF/BM25). They capture the semantic-interference half of the paper's finding (description crowding), not LLM attention dilution or instruction interference. An LLM-router plugin interface exists (`routers.py`: implement `rank(query, skills)`), but no LLM router ships: that would cost money and break determinism.
- Distractor "franchise" variants are synthetic by design (seeded, labelled `synthetic:franchise` in reports). Real-channel audits should point `--distractor-packs` at real published packs or a skills directory.
- Task files are hand-written from each skill's trigger phrases. The harness measures routing against the author's own routing contract; adversarial or paraphrased task sets are the publisher's job to add.
- Scale findings are catalog-relative. A skill "buried" at N=200 in this distractor family may survive a different channel mix. Always report the distractor strategy and seed alongside the numbers (the report does).

## Citation

```bibtex
@misc{rehman2026skillloadtest,
  author = {Habib Ur Rehman},
  title = {skill-load-test: the open harness that measures whether agents load the right skills at scale},
  year = {2026},
  howpublished = {\url{https://github.com/habib-analyst/skill-load-test}}
}
@article{liu2026lost,
  author = {Jinlin Liu and Wei Chen and Xiaojin Zhang},
  title = {Lost in Implicit Routing: How LLM Agents Fail to Load Relevant Skills at Scale},
  journal = {arXiv preprint arXiv:2610.18522},
  year = {2026}
}
```

---
Built by [Habib Ur Rehman](https://github.com/habib-analyst) · ML/AI Engineer & healthcare-AI researcher ·
[LinkedIn](https://www.linkedin.com/in/hur-dev) · [habib.top](https://habib.top)
