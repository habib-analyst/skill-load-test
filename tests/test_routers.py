from skill_load_test.catalog import Skill
from skill_load_test.routers import Bm25Router, TfidfRouter, get_router, tokenize


def _skills():
    return [
        Skill(name="book-room", description="Create a confirmed booking for a chosen room."),
        Skill(name="cancel-booking", description="Cancel the guest's active booking."),
        Skill(name="greet-guest", description="Greet the guest and offer the menu."),
    ]


def test_tokenize_lowercases_and_strips():
    assert tokenize("Book-A Room!") == ["book", "a", "room"]


def test_tfidf_ranks_relevant_first():
    r = TfidfRouter()
    ranked = r.rank("please cancel my booking", _skills())
    assert ranked[0][1].name == "cancel-booking"
    assert ranked[0][0] > ranked[1][0]


def test_bm25_ranks_relevant_first():
    r = Bm25Router()
    ranked = r.rank("please cancel my booking", _skills())
    assert ranked[0][1].name == "cancel-booking"


def test_router_is_deterministic():
    r = TfidfRouter()
    a = [s.name for _, s in r.rank("book a room", _skills())]
    b = [s.name for _, s in r.rank("book a room", _skills())]
    assert a == b


def test_get_router_dispatch():
    assert get_router("tfidf").name == "tfidf"
    assert get_router("bm25").name == "bm25"
    try:
        get_router("nope")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
