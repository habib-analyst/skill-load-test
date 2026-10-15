#!/usr/bin/env python3
"""KILL-GATE probe for Project #31 (skill-load-test).

Replicates the core finding of arXiv 2610.18522 ("Lost in Implicit Routing",
2026-10-13) against packc's own skills, CPU-only, $0, no LLM calls.

Paper finding: holding tasks + golden skills fixed while adding irrelevant
skills -> loaded-skill recall 73.6% -> 27.4%, zero-load rate 9.3% -> 51.6%
at 1,000 irrelevant skills. Explicit selection retains 73.9%.

Honest probe design (architecture-neutral, model-agnostic):
- Reference corpus: hostel-ops.pack (14 skills). Each skill declares
  `trigger` phrases = author-intended loading conditions.
- Tasks: 14 front-desk utterances, one per skill, built from its trigger
  phrases (the trigger text is the routing contract; it is metadata used to
  BUILD the tasks, never shown to the router).
- Router sees ONLY name + description per skill (exactly what progressive
  disclosure exposes before a skill is opened). Score = TF-IDF cosine.
  Deterministic, no mocks: real retrieval over real metadata.
- Implicit-load rule: load every skill with score >= tau, capped at 3 loads
  (progressive-disclosure shortlist behavior). tau is calibrated ONCE at the
  small catalog (10th percentile of golden top-1 scores there) and then FROZEN.
  A task with no skill >= tau = zero-load (paper's zero-load rate).
- Explicit-selection analog: recall@10 with the same scorer ("the needed
  skills are recognizable in a compact candidate set", paper's 73.9%).
- Distractors: real clinic.pack + restaurant.pack skills (8), plus synthetic
  franchise/vertical variants of them (documented below) with overlapping
  vocabulary, modelling a real skill channel (near-duplicate packs, shared
  terms like booking/cancel/check-in).
- Catalog scales: 14 (small), 50 (medium), 200 (large).

PASS criterion: monotone degradation of recall@3 and/or rise of zero-load
rate from 14 -> 50 -> 200. Flat = the finding does not replicate -> KILLED.
"""

import math
import os
import re
import sys
from collections import Counter

PACKC = os.path.expanduser(
    "~/workspace/goals/github-portfolio-linkedin-presence-buildout/hidden_files/packc")
sys.path.insert(0, PACKC)
from packc.parser import parse_file  # noqa: E402

TOKEN = re.compile(r"[a-z0-9]+")


def tok(s):
    return TOKEN.findall(s.lower())


class Skill:
    def __init__(self, name, description, triggers, golden=False):
        self.name = name
        self.description = description
        self.triggers = list(triggers)
        self.golden = golden

    def meta(self):
        return self.name.replace("-", " ").replace("_", " ") + " " + self.description


def load_pack(path, golden=False):
    pf = parse_file(path)
    return [Skill(s.name.strip(), s.description.strip(), s.triggers, golden)
            for s in pf.skills]


# ---------------------------------------------------------------- tasks ----
# One task per hostel skill, utterance derived from the skill's own trigger
# phrases (the author's declared routing contract).
TASK_UTTERANCES = {
    "greeting": "assalam o alaikum, I just arrived and need some help",
    "check-availability": "is there a room free for two nights starting Friday",
    "book-room": "please book a room for me, the deluxe one for the weekend",
    "cancel-booking": "I need to cancel my booking for next week",
    "modify-booking": "can I change my booking dates to next month instead",
    "check-in": "hi, I have a reservation, I would like to check in now",
    "check-out": "I am leaving today, please check me out and settle the bill",
    "late-checkout": "can I get a late checkout today, maybe until 2pm",
    "housekeeping": "please send housekeeping to clean my room",
    "payment-info": "how do I pay for my stay, do you take cards",
    "complaint": "the AC in my room is not working, this is a complaint",
    "review": "where can I leave a review of my stay here",
    "owner-digest": "send me the daily owner digest with occupancy numbers",
    "owner-approve": "approve the pending proposal for the lobby renovation",
}

# --------------------------------------- synthetic distractor variants ----
# Franchise/vertical paraphrases of the 8 real non-hostel skills. Same term
# distribution, overlapping vocabulary (booking/cancel/check-in/table) -- this
# is what a real skill channel looks like at scale.
SYNONYMS = {
    "appointment": ["booking", "reservation", "slot"],
    "cancel": ["call off", "revoke", "withdraw"],
    "book": ["reserve", "schedule"],
    "doctor": ["dentist", "physician", "specialist", "vet"],
    "clinic": ["dental clinic", "care center", "practice"],
    "table": ["seat", "spot"],
    "restaurant": ["cafe", "bistro", "eatery", "diner"],
    "order": ["request"],
    "menu": ["card"],
    "patient": ["client", "customer", "guest"],
    "guest": ["customer", "visitor", "client"],
    "room": ["suite", "chamber"],
}

VERTICALS = [
    ("dental", "dental clinic"), ("vet", "vet clinic"),
    ("physio", "physio center"), ("cafe", "cafe"),
    ("bakery", "bakery"), ("bistro", "bistro"),
]


def paraphrase(desc, seed):
    words = desc.split()
    out = []
    for i, w in enumerate(words):
        key = w.lower().strip(".,")
        if key in SYNONYMS and (seed + i) % 3 == 0:
            out.append(SYNONYMS[key][(seed + i) % len(SYNONYMS[key])])
        else:
            out.append(w)
    return " ".join(out)


def make_distractors(base_skills, n_needed, seed0=7):
    """Deterministic franchise variants of real non-hostel skills."""
    out, i = [], 0
    bi = 0
    while len(out) < n_needed:
        b = base_skills[bi % len(base_skills)]
        vert, vname = VERTICALS[(bi // len(base_skills)) % len(VERTICALS)]
        vname2 = vname
        desc = paraphrase(b.description, seed0 + i)
        desc = re.sub(r"\bclinic\b|\brestaurant\b", vname2, desc, flags=re.I)
        name = "%s-%s-%d" % (vert, b.name, i)
        out.append(Skill(name, desc, [], golden=False))
        i += 1
        bi += 1
    return out


# ---------------------------------------------------------------- router ---
def tfidf_matrix(docs):
    """docs: list of token lists. Returns (doc_vectors, idf)."""
    n = len(docs)
    df = Counter()
    tfs = []
    for d in docs:
        c = Counter(d)
        tfs.append(c)
        for t in c:
            df[t] += 1
    idf = {t: math.log((n + 1) / (df[t] + 1)) + 1.0 for t in df}
    vecs = []
    for c in tfs:
        tot = sum(c.values())
        v = {t: (cnt / tot) * idf[t] for t, cnt in c.items()}
        vecs.append(v)
    return vecs, idf


def cosine(a, b):
    dot = sum(v * b.get(t, 0.0) for t, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def run_scale(golden, distractors, catalog_size, tau):
    catalog = golden + distractors[:catalog_size - len(golden)]
    docs = [tok(s.meta()) for s in catalog]
    vecs, idf = tfidf_matrix(docs)

    def qvec(q):
        c = Counter(tok(q))
        tot = sum(c.values())
        return {t: (cnt / tot) * idf.get(t, math.log(len(docs) + 1) + 1.0)
                for t, cnt in c.items()}

    rows = []
    for g in golden:
        utt = TASK_UTTERANCES[g.name]
        q = qvec(utt)
        scored = sorted(((cosine(q, v), s) for v, s in zip(vecs, catalog)),
                        key=lambda x: -x[0])
        rank = next(i for i, (_, s) in enumerate(scored, 1) if s is g)
        loads = [s for sc, s in scored[:3] if sc >= tau]
        rows.append({
            "skill": g.name,
            "rank": rank,
            "top1_score": scored[0][0],
            "golden_score": next(sc for sc, s in scored if s is g),
            "hit3": rank <= 3,
            "hit10": rank <= 10,
            "loaded": any(s is g for s in loads),
            "zero_load": len(loads) == 0,
            "n_loads": len(loads),
        })
    return rows


def main():
    golden = load_pack(os.path.join(PACKC, "examples", "hostel-ops.pack"), golden=True)
    assert len(golden) == 14, len(golden)
    assert set(TASK_UTTERANCES) == {g.name for g in golden}
    base_d = (load_pack(os.path.join(PACKC, "examples", "clinic.pack"))
              + load_pack(os.path.join(PACKC, "examples", "restaurant.pack")))
    assert len(base_d) == 8, len(base_d)

    # calibrate tau ONCE at small catalog: 25th percentile of golden scores
    # (frozen thereafter; documented modeling choice for the implicit
    # relevance bar). Using 25th pct, not 10th, so one degenerate
    # zero-overlap task cannot pin tau to 0.
    small = run_scale(golden, [], 14, tau=0.0)
    gscores = sorted(r["golden_score"] for r in small)
    tau = gscores[int(0.25 * len(gscores))]
    print("calibrated tau (frozen): %.4f  [25th pct of golden scores @N=14]" % tau)

    distractors = make_distractors(base_d, 186)
    results = {}
    for size in (14, 50, 200):
        rows = run_scale(golden, distractors, size, tau)
        n = len(rows)
        recall3 = sum(r["hit3"] for r in rows) / n
        recall10 = sum(r["hit10"] for r in rows) / n
        zero = sum(r["zero_load"] for r in rows) / n
        loaded = sum(r["loaded"] for r in rows) / n
        mean_loads = sum(r["n_loads"] for r in rows) / n
        results[size] = dict(recall3=recall3, recall10=recall10, zero=zero,
                             loaded=loaded, mean_loads=mean_loads, rows=rows)
        print("\nN=%d  recall@3=%.3f  recall@10=%.3f  loaded=%.3f  "
              "zero_load=%.3f  mean_loads=%.2f"
              % (size, recall3, recall10, loaded, zero, mean_loads))

    print("\nper-skill hit@3 by scale:")
    for g in golden:
        line = "  %-18s" % g.name
        for size in (14, 50, 200):
            r = next(x for x in results[size]["rows"] if x["skill"] == g.name)
            line += "  N=%d:rank=%d%s" % (size, r["rank"],
                                          "" if r["hit3"] else " MISS")
        print(line)

    r14, r50, r200 = results[14], results[50], results[200]
    degrades = (r200["recall3"] < r50["recall3"] <= r14["recall3"] + 1e-9
                and r200["zero"] > r14["zero"])
    print("\nVERDICT: %s" % ("REPLICATES (degrades with scale)" if degrades
                             else "DOES NOT REPLICATE"))
    import json
    with open(os.path.expanduser("~/workspace/goals/github-portfolio-linkedin-presence-buildout"
                                 "/hidden_files/papers/skill-load-test/killgate_probe.json"),
              "w") as f:
        json.dump({str(k): {kk: vv for kk, vv in v.items() if kk != "rows"}
                   for k, v in results.items()}, f, indent=1)
    return 0 if degrades else 1


if __name__ == "__main__":
    sys.exit(main())
