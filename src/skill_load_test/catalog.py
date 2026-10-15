"""Skill catalog loading.

A Skill is the unit the harness measures: the metadata an agent sees before
opening a skill (name + description), exactly what progressive disclosure
exposes. Adapters load catalogs from:

- .pack files (packc format; best-effort regex over skill blocks)
- plain JSON catalogs: [{"name": ..., "description": ...}]
- packc publish registries: registry.json -> tarballs -> .pack inside
- Agent Skills channel dirs: directories of SKILL.md files with YAML
  frontmatter (name/description)
"""
from __future__ import annotations

import io
import json
import os
import re
import tarfile
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str
    source: str = ""
    golden: bool = False
    triggers: list = field(default_factory=list)

    def metadata_text(self) -> str:
        name_words = self.name.replace("-", " ").replace("_", " ")
        return "%s %s" % (name_words, self.description)


_SKILL_BLOCK = re.compile(r"skill\s+([A-Za-z0-9_\-]+)\s*\{(.*?)\n\}", re.DOTALL)
_DESC = re.compile(r'description\s*:\s*"((?:[^"\\]|\\.)*)"')
_TRIGGER_LIST = re.compile(r"trigger\s*:\s*\[(.*?)\]", re.DOTALL)
_TRIGGER_ITEM = re.compile(r'"((?:[^"\\]|\\.)*)"')


def load_pack_text(path: str, source: str = "", golden: bool = False) -> list:
    """Best-effort skill extraction from a packc .pack file."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    skills = []
    for m in _SKILL_BLOCK.finditer(text):
        name = m.group(1)
        body = m.group(2)
        dm = _DESC.search(body)
        if not dm:
            continue
        desc = dm.group(1).encode().decode("unicode_escape", errors="ignore")
        triggers = []
        tm = _TRIGGER_LIST.search(body)
        if tm:
            triggers = [t.encode().decode("unicode_escape", errors="ignore")
                        for t in _TRIGGER_ITEM.findall(tm.group(1))]
        skills.append(Skill(name=name, description=desc, source=source or path,
                            golden=golden, triggers=triggers))
    if not skills:
        raise ValueError("no skill blocks parsed from %s" % path)
    return skills


def load_json_catalog(path: str, golden: bool = False) -> list:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    items = data["skills"] if isinstance(data, dict) and "skills" in data else data
    skills = []
    for it in items:
        skills.append(Skill(name=it["name"], description=it.get("description", ""),
                            source=path, golden=golden,
                            triggers=it.get("triggers", [])))
    if not skills:
        raise ValueError("empty catalog in %s" % path)
    return skills


def load_registry(registry_dir: str) -> list:
    """packc publish registry: registry.json entries -> tarballs -> .pack."""
    reg_path = os.path.join(registry_dir, "registry.json")
    with open(reg_path, encoding="utf-8") as fh:
        entries = json.load(fh)
    skills = []
    for e in entries:
        tarball = os.path.join(registry_dir, e["tarball"])
        with tarfile.open(tarball, "r:gz") as tf:
            pack_member = next(
                (m for m in tf.getmembers() if m.name.endswith(".pack")), None)
            if pack_member is None:
                continue
            raw = tf.extractfile(pack_member).read().decode("utf-8")
        for m in _SKILL_BLOCK.finditer(raw):
            dm = _DESC.search(m.group(2))
            if dm:
                skills.append(Skill(
                    name=m.group(1),
                    description=dm.group(1).encode().decode("unicode_escape",
                                                           errors="ignore"),
                    source="%s@%s" % (e["name"], e.get("version", ""))))
    if not skills:
        raise ValueError("no skills extracted from registry %s" % registry_dir)
    return skills


_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_skillmd_dir(directory: str) -> list:
    """Agent Skills channel layout: one SKILL.md per skill directory."""
    skills = []
    for root, _dirs, files in os.walk(directory):
        for fn in files:
            if fn != "SKILL.md":
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            fm = _FRONTMATTER.match(text)
            name, desc = None, ""
            if fm:
                for line in fm.group(1).splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip("'\"")
                    elif line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip("'\"")
            if not name:
                name = os.path.basename(root)
            if not desc:
                # fall back to first non-empty line after frontmatter
                rest = text[fm.end():] if fm else text
                for line in rest.splitlines():
                    if line.strip():
                        desc = line.strip()[:200]
                        break
            skills.append(Skill(name=name, description=desc, source=path))
    if not skills:
        raise ValueError("no SKILL.md files under %s" % directory)
    return skills


def load_any(path: str, golden: bool = False) -> list:
    """Dispatch on path type: .pack, .json, registry dir, or SKILL.md dir."""
    if os.path.isdir(path):
        if os.path.exists(os.path.join(path, "registry.json")):
            return load_registry(path)
        return load_skillmd_dir(path)
    if path.endswith(".pack"):
        return load_pack_text(path, golden=golden)
    if path.endswith(".json"):
        return load_json_catalog(path, golden=golden)
    raise ValueError("cannot determine catalog format for %s" % path)
