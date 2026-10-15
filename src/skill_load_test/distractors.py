"""Distractor catalog construction.

An audit holds the golden pack fixed and grows the catalog by adding
irrelevant skills, mirroring the experimental design of the paper that
motivated this harness (arXiv 2610.18522): the only thing that changes
across scales is how many distractors compete for the router's attention.

Two distractor sources:
- pool: real skills from other packs / registries / SKILL.md dirs.
- franchise: deterministic synthetic variants of pool skills (paraphrased
  descriptions with vocabulary-preserving synonym swaps and vertical
  renaming). This models what real skill channels look like at scale:
  near-duplicate packs across verticals sharing terms like
  booking/cancel/check-in. Clearly labelled synthetic; seeded.
"""
from __future__ import annotations

import random
import re

from .catalog import Skill

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


def paraphrase(description: str, seed: int) -> str:
    words = description.split()
    out = []
    for i, w in enumerate(words):
        key = w.lower().strip(".,")
        if key in SYNONYMS and (seed + i) % 3 == 0:
            out.append(SYNONYMS[key][(seed + i) % len(SYNONYMS[key])])
        else:
            out.append(w)
    return " ".join(out)


def franchise_variants(pool: list, n: int, seed: int = 7) -> list:
    """Deterministic synthetic distractor variants of real pool skills."""
    if not pool:
        raise ValueError("franchise strategy needs a non-empty distractor pool")
    out = []
    i = 0
    bi = 0
    while len(out) < n:
        base = pool[bi % len(pool)]
        vert, vname = VERTICALS[(bi // len(pool)) % len(VERTICALS)]
        desc = paraphrase(base.description, seed + i)
        desc = re.sub(r"\bclinic\b|\brestaurant\b|\bhostel\b", vname, desc,
                      flags=re.IGNORECASE)
        out.append(Skill(name="%s-%s-%d" % (vert, base.name, i),
                         description=desc,
                         source="synthetic:franchise"))
        i += 1
        bi += 1
    return out


def build_catalog(golden: list, pool: list, size: int,
                  strategy: str = "franchise", seed: int = 7) -> list:
    """Golden skills first, then distractors to reach exactly `size`."""
    need = size - len(golden)
    if need < 0:
        raise ValueError("catalog size %d smaller than golden pack (%d skills)"
                         % (size, len(golden)))
    if need == 0:
        return list(golden)
    if strategy == "pool":
        if len(pool) < need:
            raise ValueError("pool has %d skills, need %d" % (len(pool), need))
        rng = random.Random(seed)
        distractors = rng.sample(pool, need)
    elif strategy == "franchise":
        distractors = franchise_variants(pool, need, seed=seed)
    else:
        raise ValueError("unknown distractor strategy %r" % strategy)
    return list(golden) + distractors
