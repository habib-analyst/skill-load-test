import os
import tempfile

from skill_load_test.catalog import (
    Skill, load_json_catalog, load_pack_text, load_registry, load_skillmd_dir,
)

PACK = """pack demo {
  name: "demo",
  version: "0.1.0",
  description: "demo pack",
  author: "t",
  tools: ["tool_a"],
}

skill alpha-skill {
  description: "Does alpha things for guests.",
  trigger: ["do alpha", "alpha please"],
  input: X,
  output: Y,
  tool: "tool_a",
  steps: ["Step one."],
}

skill beta_skill {
  description: "Handles beta bookings.",
  trigger: ["book beta"],
  input: X,
  output: Y,
  tool: "tool_a",
  steps: ["Step one."],
}
"""


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def test_pack_text_parses_skills():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "demo.pack")
        _write(p, PACK)
        skills = load_pack_text(p, golden=True)
    assert len(skills) == 2
    assert skills[0].name == "alpha-skill"
    assert "alpha things" in skills[0].description
    assert skills[0].triggers == ["do alpha", "alpha please"]
    assert skills[0].golden is True
    assert skills[1].name == "beta_skill"


def test_pack_text_rejects_empty():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "empty.pack")
        _write(p, "pack x { name: \"x\" }\n")
        try:
            load_pack_text(p)
        except ValueError:
            return
    raise AssertionError("expected ValueError")


def test_json_catalog():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "c.json")
        _write(p, '[{"name": "s1", "description": "first skill"}, '
                  '{"name": "s2", "description": "second skill"}]')
        skills = load_json_catalog(p)
    assert [s.name for s in skills] == ["s1", "s2"]
    assert skills[1].description == "second skill"


def test_metadata_text_denormalizes_name():
    s = Skill(name="check-in", description="Check the guest in.")
    assert "check in" in s.metadata_text()


def test_skillmd_dir_adapter():
    with tempfile.TemporaryDirectory() as d:
        sd = os.path.join(d, "my-skill")
        os.makedirs(sd)
        _write(os.path.join(sd, "SKILL.md"),
               "---\nname: my-skill\ndescription: A test skill.\n---\n\nBody.\n")
        skills = load_skillmd_dir(d)
    assert len(skills) == 1
    assert skills[0].name == "my-skill"
    assert skills[0].description == "A test skill."


def test_registry_adapter(tmp_path=None):
    import tarfile
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        pack_src = os.path.join(d, "p.pack")
        _write(pack_src, PACK)
        stage = os.path.join(d, "stage", "demo-0.1.0")
        os.makedirs(stage)
        _write(os.path.join(stage, "demo.pack"), PACK)
        tarball = os.path.join(d, "demo-0.1.0.tar.gz")
        with tarfile.open(tarball, "w:gz") as tf:
            tf.add(stage, arcname="demo-0.1.0")
        _write(os.path.join(d, "registry.json"), json.dumps([{
            "name": "demo", "version": "0.1.0", "tarball": "demo-0.1.0.tar.gz",
            "skills": 2}]))
        skills = load_registry(d)
    assert len(skills) == 2
    assert skills[0].source == "demo@0.1.0"
