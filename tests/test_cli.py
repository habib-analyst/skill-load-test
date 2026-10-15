import os
import tempfile

from skill_load_test.cli import build_parser, main

PACK = """pack demo {
  name: "demo",
  version: "0.1.0",
  description: "demo",
  author: "t",
  tools: ["tool_a"],
}
skill alpha {
  description: "Do alpha things for hotel guests.",
  trigger: ["do alpha"],
  input: X,
  output: Y,
  tool: "tool_a",
  steps: ["One."],
}
skill beta {
  description: "Handle beta bookings and rooms.",
  trigger: ["book beta"],
  input: X,
  output: Y,
  tool: "tool_a",
  steps: ["One."],
}
"""

DISTRACT = """pack dist {
  name: "dist",
  version: "0.1.0",
  description: "d",
  author: "t",
  tools: ["tool_a"],
}
skill gamma {
  description: "Cancel clinic appointments politely.",
  trigger: ["cancel it"],
  input: X,
  output: Y,
  tool: "tool_a",
  steps: ["One."],
}
"""


def _write(p, text):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def test_cli_audit_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        pack = os.path.join(d, "demo.pack")
        dist = os.path.join(d, "dist.pack")
        tasks = os.path.join(d, "t.jsonl")
        out = os.path.join(d, "report.md")
        _write(pack, PACK)
        _write(dist, DISTRACT)
        _write(tasks, '{"id": "t1", "utterance": "do alpha now", "golden": ["alpha"]}\n'
                       '{"id": "t2", "utterance": "book beta room", "golden": ["beta"]}\n')
        rc = main(["audit", pack, "--tasks", tasks,
                   "--catalog-sizes", "2,3",
                   "--distractor-packs", dist,
                   "--distractor-strategy", "pool",
                   "--out", out])
        assert rc == 0
        text = open(out).read()
        assert "skill-load-test audit: demo" in text
        assert "alpha" in text


def test_cli_rejects_oversized_small_catalog():
    with tempfile.TemporaryDirectory() as d:
        pack = os.path.join(d, "demo.pack")
        tasks = os.path.join(d, "t.jsonl")
        _write(pack, PACK)
        _write(tasks, '{"id": "t1", "utterance": "x", "golden": ["alpha"]}\n')
        try:
            main(["audit", pack, "--tasks", tasks, "--catalog-sizes", "1"])
        except SystemExit as e:
            assert e.code != 0
            return
    raise AssertionError("expected SystemExit")


def test_parser_defaults():
    args = build_parser().parse_args(["audit", "p.pack", "--tasks", "t.jsonl"])
    assert args.router == "tfidf"
    assert args.catalog_sizes == "14,50,200"
    assert args.distractor_strategy == "franchise"
