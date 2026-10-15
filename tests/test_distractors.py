from skill_load_test.catalog import Skill
from skill_load_test.distractors import (
    build_catalog, franchise_variants, paraphrase,
)


def _pool():
    return [Skill(name="cancel-appointment",
                  description="Cancel an appointment at the clinic.")]


def test_franchise_count_and_determinism():
    a = franchise_variants(_pool(), 10, seed=7)
    b = franchise_variants(_pool(), 10, seed=7)
    assert len(a) == 10
    assert [s.name for s in a] == [s.name for s in b]
    assert [s.description for s in a] == [s.description for s in b]


def test_franchise_seed_changes_output():
    a = franchise_variants(_pool(), 10, seed=7)
    b = franchise_variants(_pool(), 10, seed=99)
    assert [s.description for s in a] != [s.description for s in b]


def test_franchise_marks_synthetic_source():
    vs = franchise_variants(_pool(), 3, seed=7)
    assert all(s.source == "synthetic:franchise" for s in vs)
    assert all(not s.golden for s in vs)


def test_paraphrase_preserves_meaning_words():
    out = paraphrase("Cancel an appointment at the clinic.", seed=7)
    # synonym swap applied ("appointment" -> "booking"); vertical rename is
    # franchise_variants' job, not paraphrase's
    assert "booking" in out
    assert isinstance(out, str) and len(out) > 10


def test_build_catalog_exact_size_and_golden_first():
    golden = [Skill(name="g1", description="golden one", golden=True)]
    cat = build_catalog(golden, _pool(), 5, strategy="franchise", seed=7)
    assert len(cat) == 5
    assert cat[0].golden is True
    assert sum(s.golden for s in cat) == 1


def test_build_catalog_rejects_small_size():
    golden = [Skill(name="g1", description="x", golden=True)] * 3
    try:
        build_catalog(golden, _pool(), 2)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
