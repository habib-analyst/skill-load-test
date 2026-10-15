"""The audit engine.

For each catalog size: build the catalog (golden pack + distractors), rank
every task's utterance with the router, apply the implicit-load rule, and
record per-skill outcomes.

Implicit-load rule (architecture-neutral model of "the agent decides whether
to open a skill while executing"): a skill is LOADED iff its score clears an
absolute relevance bar tau, capped at `max_loads` skills (progressive
disclosure shortlist). tau is calibrated ONCE at the smallest catalog size
(`tau_quantile` of golden-skill scores there) and then frozen, so score
deflation under distractor interference can surface as zero-loads, exactly
the failure signature the motivating paper reports for LLM agents.

Explicit-selection analog: recall@k at a wide k (default 10) with the same
scorer, i.e. "is the needed skill recognizable inside a compact candidate
set" (the paper's preselection baseline).

Failure-mode taxonomy per task (at each scale):
- ok: golden skill loaded.
- outranked: golden in top-10 but outside the top-3 shortlist
  (semantic interference from distractor descriptions).
- skipped: golden inside top-3 but below tau (the bar the small catalog set).
- buried: golden beyond top-10.
- gap=True additionally marks skills that miss even at the smallest catalog
  (pre-existing metadata gap, not a scale effect).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Task:
    id: str
    utterance: str
    golden: list


def load_tasks(path: str) -> list:
    tasks = []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            it = json.loads(line)
            golden = it["golden"] if isinstance(it["golden"], list) else [it["golden"]]
            tasks.append(Task(id=it.get("id", "t%d" % ln),
                              utterance=it["utterance"], golden=golden))
    if not tasks:
        raise ValueError("no tasks in %s" % path)
    return tasks


@dataclass
class AuditConfig:
    sizes: list = field(default_factory=lambda: [14, 50, 200])
    router: str = "tfidf"
    topk_shortlist: int = 3
    recall_k_wide: int = 10
    max_loads: int = 3
    tau_quantile: float = 0.25
    distractor_strategy: str = "franchise"
    seed: int = 7


def _quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0.0
    idx = min(len(xs) - 1, int(q * len(xs)))
    return xs[idx]


def calibrate_tau(router, tasks, catalog, quantile=0.25):
    """Relevance bar from golden-skill scores at the small catalog."""
    by_name = {s.name: s for s in catalog}
    scores = []
    for t in tasks:
        ranked = router.rank(t.utterance, catalog)
        pos = {s.name: (i, sc) for i, (sc, s) in enumerate(ranked)}
        for g in t.golden:
            if g in pos:
                scores.append(pos[g][1])
    return _quantile(scores, quantile)


def classify(rank, score, loaded, tau):
    if loaded:
        return "ok"
    if rank is None:
        return "buried"
    if rank <= 3 and score < tau:
        return "skipped"
    if rank <= 10:
        return "outranked"
    return "buried"


def run_audit(golden, pool, tasks, config, router):
    from .distractors import build_catalog

    sizes = sorted(config.sizes)
    small_catalog = build_catalog(golden, pool, sizes[0],
                                  strategy=config.distractor_strategy,
                                  seed=config.seed)
    tau = calibrate_tau(router, tasks, small_catalog,
                        quantile=config.tau_quantile)

    scale_results = {}
    for size in sizes:
        catalog = build_catalog(golden, pool, size,
                                strategy=config.distractor_strategy,
                                seed=config.seed)
        rows = []
        for t in tasks:
            ranked = router.rank(t.utterance, catalog)
            pos = {s.name: (i + 1, sc) for i, (sc, s) in enumerate(ranked)}
            loads = [(sc, s) for sc, s in ranked[:config.topk_shortlist]
                     if sc >= tau][:config.max_loads]
            loaded_names = {s.name for _, s in loads}
            for g in t.golden:
                rank, score = pos.get(g, (None, 0.0))
                is_loaded = g in loaded_names
                rows.append({
                    "task": t.id,
                    "skill": g,
                    "rank": rank,
                    "score": round(score, 4),
                    "loaded": is_loaded,
                    "zero_load": len(loads) == 0,
                    "n_loads": len(loads),
                    "hit1": rank == 1,
                    "hit3": rank is not None and rank <= 3,
                    "hit10": rank is not None and rank <= config.recall_k_wide,
                    "taxonomy": classify(rank, score, is_loaded, tau),
                })
        n = len(rows)
        agg = {
            "catalog_size": size,
            "n_tasks": n,
            "tau": round(tau, 4),
            "recall@1": round(sum(r["hit1"] for r in rows) / n, 4),
            "recall@3": round(sum(r["hit3"] for r in rows) / n, 4),
            "recall@10": round(sum(r["hit10"] for r in rows) / n, 4),
            "loaded_rate": round(sum(r["loaded"] for r in rows) / n, 4),
            "zero_load_rate": round(sum(r["zero_load"] for r in rows) / n, 4),
            "mean_loads": round(sum(r["n_loads"] for r in rows) / n, 3),
            "taxonomy_counts": {k: sum(1 for r in rows if r["taxonomy"] == k)
                                for k in ("ok", "outranked", "skipped", "buried")},
            "rows": rows,
        }
        scale_results[size] = agg

    # gap flag: misses even at the smallest catalog (not a scale effect)
    small_rows = {(r["task"], r["skill"]): r
                  for r in scale_results[sizes[0]]["rows"]}
    for size in sizes:
        for r in scale_results[size]["rows"]:
            r["gap_at_smallest"] = not small_rows[(r["task"], r["skill"])]["loaded"]

    return {
        "config": {
            "sizes": sizes,
            "router": router.name,
            "topk_shortlist": config.topk_shortlist,
            "recall_k_wide": config.recall_k_wide,
            "max_loads": config.max_loads,
            "tau_quantile": config.tau_quantile,
            "distractor_strategy": config.distractor_strategy,
            "seed": config.seed,
            "n_golden": len(golden),
            "pool_size": len(pool),
        },
        "tau": round(tau, 4),
        "scales": scale_results,
    }
