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
    assert "' btn-primary '" in cand.expression
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


def test_by_class_uses_safe_multiclass_pattern():
    """by_class must NOT match a partial class (regression for substring bug)."""
    candidates = generate_candidates(
        tag="button", text=None, attributes={"class": "btn"}
    )
    cand = next(c for c in candidates if c.strategy == "by_class")
    assert "concat(' '" in cand.expression
    assert "normalize-space(@class)" in cand.expression
    assert "' btn '" in cand.expression


def test_by_class_first_class_with_multiclass_attr():
    candidates = generate_candidates(
        tag="button", text=None, attributes={"class": "btn btn-primary"}
    )
    cand = next(c for c in candidates if c.strategy == "by_class")
    assert (
        cand.expression
        == "//button[contains(concat(' ', normalize-space(@class), ' '), ' btn ')]"
    )


def test_split_dynamic_id_digits_only_suffix():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("vpu_amount_20260512") == "vpu_amount_"
    assert _split_dynamic_id("user-123") == "user-"


def test_split_dynamic_id_uuid_like():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("field_a1b2c3d4") == "field_"


def test_split_dynamic_id_date_with_dashes():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("foo_2026-05-12") == "foo_"


def test_split_dynamic_id_static_returns_none():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("login") is None
    assert _split_dynamic_id("foo_ab") is None
    assert _split_dynamic_id("user_name") is None


def test_split_dynamic_id_short_prefix_rejected():
    from xpath_detector.analyzer import _split_dynamic_id

    assert _split_dynamic_id("a_123") is None


def test_by_id_prefix_generated_for_dynamic_id():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "vpu_amount_20260512"}
    )
    cand = next(c for c in candidates if c.strategy == "by_id_prefix")
    assert cand.expression == "//input[starts-with(@id,'vpu_amount_')]"
    assert cand.stability_score == 85


def test_by_id_prefix_NOT_generated_for_static_id():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "login"}
    )
    assert not any(c.strategy == "by_id_prefix" for c in candidates)


def test_by_id_prefix_coexists_with_by_id():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"id": "foo_123"}
    )
    strategies = [c.strategy for c in candidates]
    assert "by_id" in strategies
    assert "by_id_prefix" in strategies


def test_by_attr_combo_skipped_when_id_present():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={"id": "x", "name": "amount", "type": "text"},
    )
    assert not any(c.strategy == "by_attr_combo" for c in candidates)


def test_by_attr_combo_skipped_with_single_attr():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"name": "amount"}
    )
    assert not any(c.strategy == "by_attr_combo" for c in candidates)


def test_by_attr_combo_name_and_type():
    candidates = generate_candidates(
        tag="input", text=None, attributes={"name": "amount", "type": "text"}
    )
    cand = next(c for c in candidates if c.strategy == "by_attr_combo")
    assert cand.expression == "//input[@name='amount' and @type='text']"
    assert cand.stability_score == 88


def test_by_attr_combo_picks_first_two_by_priority():
    candidates = generate_candidates(
        tag="input",
        text=None,
        attributes={
            "placeholder": "0.00",
            "role": "spinbutton",
            "name": "amount",
            "type": "number",
        },
    )
    cand = next(c for c in candidates if c.strategy == "by_attr_combo")
    assert cand.expression == "//input[@name='amount' and @type='number']"
