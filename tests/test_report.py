from skill_load_test.audit import (
    AuditConfig, Task, run_audit,
)
from skill_load_test.catalog import Skill
from skill_load_test.report import render_json, render_markdown
from skill_load_test.routers import TfidfRouter
import json


def _result():
    golden = [Skill(name="book-room", golden=True,
                    description="Create a confirmed booking for a room."),
              Skill(name="cancel-booking", golden=True,
                    description="Cancel the guest's active booking.")]
    pool = [Skill(name="cancel-appointment",
                  description="Cancel an appointment at the clinic.")]
    tasks = [Task(id="t1", utterance="book a room", golden=["book-room"]),
             Task(id="t2", utterance="cancel my booking", golden=["cancel-booking"])]
    cfg = AuditConfig(sizes=[2, 3], distractor_strategy="pool", seed=7)
    return run_audit(golden, pool, tasks, cfg, TfidfRouter())


def test_markdown_has_tables_and_taxonomy():
    md = render_markdown(_result(), "demo-pack")
    assert "# skill-load-test audit: demo-pack" in md
    assert "## Load reliability vs catalog size" in md
    assert "## Failure-mode taxonomy" in md
    assert "## Per-skill outcome" in md
    assert "book-room" in md
    assert "| catalog size |" in md


def test_json_roundtrips():
    data = json.loads(render_json(_result()))
    assert data["config"]["router"] == "tfidf"
    assert sorted(data["scales"]) == ["2", "3"] or sorted(
        int(x) for x in data["scales"]) == [2, 3]
