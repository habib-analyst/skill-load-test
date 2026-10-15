#!/usr/bin/env python3
"""Reproduce the reference audit numbers quoted in README.md.

Runs the hostel-ops and clinic reference audits against the packc example
packs and prints the scale tables. Deterministic: same seed, same numbers.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACKC = os.path.expanduser("~/workspace/goals/github-portfolio-linkedin-presence-buildout"
                           "/hidden_files/packc/examples")
OUT = os.path.join(HERE, "reference_reports")
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("hostel-ops", "hostel_tasks.jsonl", "14,50,200"),
    ("clinic", "clinic_tasks.jsonl", "4,20,100"),
]

for pack, tasks, sizes in JOBS:
    cmd = [sys.executable, "-m", "skill_load_test", "audit",
           os.path.join(PACKC, pack + ".pack"),
           "--tasks", os.path.join(HERE, tasks),
           "--catalog-sizes", sizes,
           "--distractor-packs",
           os.path.join(PACKC, "clinic.pack" if pack == "hostel-ops" else "hostel-ops.pack"),
           os.path.join(PACKC, "restaurant.pack"),
           "--out", os.path.join(OUT, pack + ".md"),
           "--json-out", os.path.join(OUT, pack + ".json")]
    print("$", " ".join(cmd))
    r = subprocess.run(cmd, cwd=os.path.join(HERE, ".."))
    if r.returncode not in (0, 2):
        sys.exit("audit failed for %s" % pack)
print("reports in", OUT)
