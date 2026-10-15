"""Report rendering: Markdown (human) + JSON (machine)."""
from __future__ import annotations

import json


def render_markdown(result, pack_name: str) -> str:
    cfg = result["config"]
    sizes = sorted(result["scales"])
    L = []
    L.append("# skill-load-test audit: %s" % pack_name)
    L.append("")
    L.append("Router: `%s` | distractor strategy: `%s` (seed %d) | "
             "tau=%.4f (frozen, calibrated at N=%d) | shortlist top-%d, "
             "max %d loads" % (
                 cfg["router"], cfg["distractor_strategy"], cfg["seed"],
                 result["tau"], sizes[0], cfg["topk_shortlist"],
                 cfg["max_loads"]))
    L.append("")
    L.append("## Load reliability vs catalog size")
    L.append("")
    L.append("| catalog size | recall@1 | recall@3 | recall@10 | loaded | "
             "zero-load | mean loads |")
    L.append("|---|---|---|---|---|---|---|")
    for s in sizes:
        a = result["scales"][s]
        L.append("| %d | %.3f | %.3f | %.3f | %.3f | %.3f | %.2f |" % (
            s, a["recall@1"], a["recall@3"], a["recall@10"],
            a["loaded_rate"], a["zero_load_rate"], a["mean_loads"]))
    L.append("")
    L.append("recall@10 is the explicit-selection analog: is the needed skill "
             "recognizable inside a compact candidate set. `loaded` applies "
             "the implicit-load rule (score >= tau, top-%d shortlist)." %
             cfg["topk_shortlist"])
    L.append("")
    L.append("## Failure-mode taxonomy (largest catalog, N=%d)" % sizes[-1])
    L.append("")
    big = result["scales"][sizes[-1]]
    tc = big["taxonomy_counts"]
    L.append("| mode | tasks | meaning |")
    L.append("|---|---|---|")
    L.append("| ok | %d | golden skill loaded |" % tc["ok"])
    L.append("| outranked | %d | golden in top-10 but outside the top-3 "
             "shortlist: semantic interference from distractor descriptions |"
             % tc["outranked"])
    L.append("| skipped | %d | golden in top-3 but below the frozen tau: "
             "score deflation under interference |" % tc["skipped"])
    L.append("| buried | %d | golden beyond top-10 |" % tc["buried"])
    L.append("")
    L.append("## Per-skill outcome at N=%d" % sizes[-1])
    L.append("")
    L.append("| skill | rank | score | loaded | taxonomy | gap at smallest |")
    L.append("|---|---|---|---|---|---|")
    for r in big["rows"]:
        L.append("| %s | %s | %.4f | %s | %s | %s |" % (
            r["skill"], r["rank"], r["score"],
            "yes" if r["loaded"] else "no", r["taxonomy"],
            "yes (pre-existing)" if r["gap_at_smallest"] else "no"))
    L.append("")
    L.append("_gap at smallest = misses even at the smallest catalog: a "
             "metadata/description gap, not a scale effect. Fix the skill "
             "description, not the router._")
    L.append("")
    return "\n".join(L)


def render_json(result) -> str:
    return json.dumps(result, indent=1)
