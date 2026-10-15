"""CLI: skill-load-test audit <pack> --tasks ... --catalog-sizes ..."""
from __future__ import annotations

import argparse
import os
import sys


def _find_pack_file(pack_path):
    if os.path.isfile(pack_path):
        return pack_path
    if os.path.isdir(pack_path):
        packs = [os.path.join(pack_path, f) for f in os.listdir(pack_path)
                 if f.endswith(".pack")]
        if len(packs) == 1:
            return packs[0]
        if not packs:
            raise SystemExit("no .pack file in %s" % pack_path)
        raise SystemExit("multiple .pack files in %s; pass one directly"
                         % pack_path)
    raise SystemExit("pack not found: %s" % pack_path)


def cmd_audit(args):
    from .audit import AuditConfig, load_tasks, run_audit
    from .catalog import load_any, load_pack_text
    from .report import render_json, render_markdown
    from .routers import get_router

    pack_file = _find_pack_file(args.pack)
    golden = load_pack_text(pack_file, golden=True)
    pool = []
    for dp in args.distractor_packs or []:
        pool.extend(load_any(dp))
    pool = [s for s in pool if s.name not in {g.name for g in golden}]
    if not pool:
        raise SystemExit("empty distractor pool: pass --distractor-packs")

    tasks = load_tasks(args.tasks)
    sizes = sorted({int(x) for x in args.catalog_sizes.split(",")})
    if sizes[0] < len(golden):
        raise SystemExit("smallest catalog size must be >= golden skills (%d)"
                         % len(golden))

    config = AuditConfig(
        sizes=sizes, router=args.router,
        topk_shortlist=args.shortlist, max_loads=args.max_loads,
        tau_quantile=args.tau_quantile,
        distractor_strategy=args.distractor_strategy, seed=args.seed)
    router = get_router(args.router)
    result = run_audit(golden, pool, tasks, config, router)

    pack_name = os.path.splitext(os.path.basename(pack_file))[0]
    md = render_markdown(result, pack_name)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print("wrote %s" % args.out)
    else:
        print(md)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(render_json(result))
        print("wrote %s" % args.json_out)
    # nonzero exit if the largest catalog loses >25pp recall@3 vs smallest
    small = result["scales"][sizes[0]]
    big = result["scales"][sizes[-1]]
    drop = small["recall@3"] - big["recall@3"]
    print("recall@3 %d -> %d: %.3f -> %.3f (drop %.3f)" % (
        sizes[0], sizes[-1], small["recall@3"], big["recall@3"], drop))
    return 2 if drop > 0.25 else 0


def build_parser():
    p = argparse.ArgumentParser(prog="skill-load-test",
                                description="Measure whether agents load the "
                                            "right skills as the catalog grows.")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="audit a pack at several catalog sizes")
    a.add_argument("pack", help=".pack file or dir containing one")
    a.add_argument("--tasks", required=True, help="tasks JSONL file")
    a.add_argument("--catalog-sizes", default="14,50,200")
    a.add_argument("--distractor-packs", nargs="*", default=[],
                   help=".pack/.json/registry/SKILL.md dirs for distractors")
    a.add_argument("--distractor-strategy", default="franchise",
                   choices=["franchise", "pool"])
    a.add_argument("--router", default="tfidf", choices=["tfidf", "bm25"])
    a.add_argument("--shortlist", type=int, default=3)
    a.add_argument("--max-loads", type=int, default=3)
    a.add_argument("--tau-quantile", type=float, default=0.25)
    a.add_argument("--seed", type=int, default=7)
    a.add_argument("--out", default=None)
    a.add_argument("--json-out", default=None)
    a.set_defaults(func=cmd_audit)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
