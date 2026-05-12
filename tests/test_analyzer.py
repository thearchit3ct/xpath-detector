from xpath_detector.analyzer import escape_xpath_literal, generate_candidates


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


def test_generate_by_class():
    candidates = generate_candidates(tag="button", text=None, attributes={"class": "btn-primary"})
    cand = next(c for c in candidates if c.strategy == "by_class")
    assert "contains(@class,'btn-primary')" in cand.expression
    assert cand.stability_score == 60


def test_generate_absolute_fallback():
    candidates = generate_candidates(
        tag="div", text=None, attributes={}, absolute_xpath="/html/body/div[3]"
    )
    cand = next(c for c in candidates if c.strategy == "absolute")
    assert cand.expression == "/html/body/div[3]"
    assert cand.stability_score == 10


def test_candidates_sorted_by_score_desc():
    candidates = generate_candidates(
        tag="input",
        text="Login",
        attributes={"id": "x", "name": "y", "class": "z"},
    )
    scores = [c.stability_score for c in candidates]
    assert scores == sorted(scores, reverse=True)


def test_escape_xpath_empty_string():
    assert escape_xpath_literal("") == "''"


def test_escape_xpath_only_apostrophe():
    result = escape_xpath_literal("'")
    assert result == "concat('', \"'\", '')"


def test_escape_xpath_wrapped_with_apostrophes():
    result = escape_xpath_literal("'x'")
    assert result == "concat('', \"'\", 'x', \"'\", '')"


def test_escape_xpath_consecutive_apostrophes():
    result = escape_xpath_literal("x''y")
    assert result == "concat('x', \"'\", '', \"'\", 'y')"


def test_generate_by_label_neighbor():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={},
        nearby_label="Compte beneficiaire :",
    )
    cand = next(c for c in candidates if c.strategy == "by_label_neighbor")
    assert cand.expression == "//span[contains(.,'Compte beneficiaire :')]/../../td/input"
    assert cand.stability_score == 50


def test_by_label_neighbor_escapes_apostrophe():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={},
        nearby_label="Reference donneur d'ordre :",
    )
    cand = next(c for c in candidates if c.strategy == "by_label_neighbor")
    assert "concat(" in cand.expression


def test_by_label_neighbor_skipped_if_none():
    candidates = generate_candidates(tag="input", text=None, attributes={"id": "x"})
    assert not any(c.strategy == "by_label_neighbor" for c in candidates)
