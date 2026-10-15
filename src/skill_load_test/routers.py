"""Routers: deterministic, CPU-only, stdlib-only retrieval over skill metadata.

The router is the architecture-neutral stand-in for an agent's implicit
routing step: given a task utterance and the full catalog of skill metadata
(name + description, exactly what progressive disclosure exposes), it ranks
skills by relevance. Two classic lexical routers ship:

- TfidfRouter: TF-IDF cosine similarity.
- Bm25Router: Okapi BM25 (k1=1.5, b=0.75).

Both are deterministic and dependency-free. A Router is any object with a
``name`` attribute and a ``rank(query, skills)`` method returning
[(score, skill)] sorted best-first, so custom routers (e.g. embedding-based)
can be plugged in without touching the audit engine.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list:
    return _TOKEN.findall(text.lower())


class TfidfRouter:
    name = "tfidf"

    def rank(self, query, skills):
        docs = [tokenize(s.metadata_text()) for s in skills]
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
            vecs.append({t: (cnt / tot) * idf[t] for t, cnt in c.items()})
        qc = Counter(tokenize(query))
        qtot = sum(qc.values()) or 1
        qv = {t: (cnt / qtot) * idf.get(t, math.log(n + 1) + 1.0)
              for t, cnt in qc.items()}
        scored = []
        for v, s in zip(vecs, skills):
            dot = sum(x * v.get(t, 0.0) for t, x in qv.items())
            nv = math.sqrt(sum(x * x for x in v.values()))
            nq = math.sqrt(sum(x * x for x in qv.values()))
            score = dot / (nv * nq) if nv and nq else 0.0
            scored.append((score, s))
        scored.sort(key=lambda x: -x[0])
        return scored


class Bm25Router:
    name = "bm25"

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def rank(self, query, skills):
        docs = [tokenize(s.metadata_text()) for s in skills]
        n = len(docs)
        df = Counter()
        tfs = []
        lens = []
        for d in docs:
            c = Counter(d)
            tfs.append(c)
            lens.append(len(d))
            for t in c:
                df[t] += 1
        avgdl = sum(lens) / n if n else 0.0
        idf = {t: math.log((n - df[t] + 0.5) / (df[t] + 0.5) + 1.0)
               for t in df}
        qterms = tokenize(query)
        scored = []
        for c, dl, s in zip(tfs, lens, skills):
            score = 0.0
            for t in qterms:
                if t not in c:
                    continue
                tf = c[t]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / avgdl)
                score += idf.get(t, 0.0) * (tf * (self.k1 + 1)) / denom
            scored.append((score, s))
        scored.sort(key=lambda x: -x[0])
        return scored


ROUTERS = {"tfidf": TfidfRouter, "bm25": Bm25Router}


def get_router(name: str):
    try:
        return ROUTERS[name]()
    except KeyError:
        raise ValueError("unknown router %r (choose from %s)"
                         % (name, sorted(ROUTERS)))
