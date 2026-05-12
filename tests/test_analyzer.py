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


def test_generate_by_data_testid():
    candidates = generate_candidates(tag="button", text=None, attributes={"data-testid": "submit"})
    cand = next(c for c in candidates if c.strategy == "by_data_testid")
    assert cand.expression == "//button[@data-testid='submit']"
    assert cand.stability_score == 90


def test_generate_by_name():
    candidates = generate_candidates(tag="input", text=None, attributes={"name": "username"})
    cand = next(c for c in candidates if c.strategy == "by_name")
    assert cand.expression == "//input[@name='username']"
    assert cand.stability_score == 80


def test_generate_by_aria_label():
    candidates = generate_candidates(tag="button", text=None, attributes={"aria-label": "Close"})
    cand = next(c for c in candidates if c.strategy == "by_aria_label")
    assert cand.expression == "//button[@aria-label='Close']"
    assert cand.stability_score == 75


def test_generate_by_text():
    candidates = generate_candidates(tag="a", text="Valider", attributes={})
    cand = next(c for c in candidates if c.strategy == "by_text")
    assert cand.expression == "//a[contains(.,'Valider')]"
    assert cand.stability_score == 70


def test_by_text_escapes_apostrophe():
    candidates = generate_candidates(tag="a", text="L'utilisateur", attributes={})
    cand = next(c for c in candidates if c.strategy == "by_text")
    assert "concat(" in cand.expression


def test_by_text_skipped_if_too_long():
    long_text = "a" * 80
    candidates = generate_candidates(tag="div", text=long_text, attributes={})
    assert not any(c.strategy == "by_text" for c in candidates)


def test_by_text_skipped_if_empty():
    candidates = generate_candidates(tag="div", text="", attributes={})
    assert not any(c.strategy == "by_text" for c in candidates)
