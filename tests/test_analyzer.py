from xpath_detector.analyzer import escape_xpath_literal, generate_candidates
from xpath_detector.models import XPathCandidate


def test_generate_by_id():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "login", "type": "text"},
    )
    by_id = next(c for c in candidates if c.strategy == "by_id")
    assert by_id.expression == "//input[@id='login']"
    assert by_id.stability_score == 95


def test_escape_xpath_simple():
    assert escape_xpath_literal("hello") == "'hello'"


def test_escape_xpath_with_apostrophe():
    result = escape_xpath_literal("L'utilisateur")
    assert result == "concat('L', \"'\", 'utilisateur')"
