import os
import tempfile

from skill_load_test.audit import (
    AuditConfig, Task, calibrate_tau, classify, load_tasks, run_audit,
)
from skill_load_test.catalog import Skill
from skill_load_test.routers import TfidfRouter


def _golden():
    return [
        Skill(name="book-room", golden=True,
              description="Create a confirmed booking for a chosen room and dates."),
        Skill(name="cancel-booking", golden=True,
              description="Cancel the guest's active booking."),
    ]


def _pool():
    return [Skill(name="cancel-appointment",
                  description="Cancel an appointment at the clinic."),
            Skill(name="book-table",
                  description="Book a table at the restaurant.")]


def _tasks():
    return [Task(id="t1", utterance="please book a room for Friday",
                 golden=["book-room"]),
            Task(id="t2", utterance="cancel my booking now",
                 golden=["cancel-booking"])]


def test_classify_taxonomy():
    assert classify(1, 0.9, True, 0.1) == "ok"
    assert classify(5, 0.9, False, 0.1) == "outranked"
    assert classify(2, 0.05, False, 0.1) == "skipped"
    assert classify(42, 0.01, False, 0.1) == "buried"
    assert classify(None, 0.0, False, 0.1) == "buried"


def test_load_tasks_jsonl():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.jsonl")
        with open(p, "w") as fh:
            fh.write('{"id": "a", "utterance": "hi", "golden": "s1"}\n')
            fh.write('{"utterance": "yo", "golden": ["s2"]}\n')
        tasks = load_tasks(p)
    assert len(tasks) == 2
    assert tasks[0].golden == ["s1"]
    assert tasks[1].id == "t2"


def test_calibrate_tau_positive_and_frozen():
    router = TfidfRouter()
    tau = calibrate_tau(router, _tasks(), _golden(), quantile=0.25)
    assert tau > 0


def test_run_audit_small_scale_perfect():
    router = TfidfRouter()
    cfg = AuditConfig(sizes=[2], distractor_strategy="pool", seed=7)
    # pool strategy needs >= need distractors; size 2 == golden count -> no pool use
    res = run_audit(_golden(), _pool(), _tasks(), cfg, router)
    a = res["scales"][2]
    assert a["recall@3"] == 1.0
    assert a["zero_load_rate"] == 0.0
    assert res["tau"] > 0


def test_run_audit_reports_taxonomy_and_gap_flags():
    router = TfidfRouter()
    cfg = AuditConfig(sizes=[2, 4], distractor_strategy="pool", seed=7)
    res = run_audit(_golden(), _pool(), _tasks(), cfg, router)
    for size in (2, 4):
        a = res["scales"][size]
        assert set(a["taxonomy_counts"]) == {"ok", "outranked", "skipped", "buried"}
        assert sum(a["taxonomy_counts"].values()) == a["n_tasks"]
        for r in a["rows"]:
            assert "gap_at_smallest" in r
