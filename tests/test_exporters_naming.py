from xpath_detector.exporters._naming import (
    dedup_name,
    sanitize,
    to_constant,
    to_pascal,
    to_var_name,
)
from xpath_detector.models import Element, XPathCandidate


def _elem(description="", text=None, name=None, tag="input"):
    attrs = {"name": name} if name else {}
    return Element(
        tag=tag,
        text=text,
        attributes=attrs,
        xpaths=[XPathCandidate("by_id", "//x", 95)],
        is_visible=True,
        is_enabled=True,
        description=description,
    )


def test_sanitize_replaces_special_chars():
    assert sanitize("hello world!") == "hello_world_"


def test_sanitize_truncates_to_50():
    assert len(sanitize("a" * 100)) == 50


def test_to_pascal_simple():
    assert to_pascal("login") == "Login"


def test_to_pascal_with_separator():
    assert to_pascal("create-transfert") == "CreateTransfert"


def test_to_pascal_empty_fallback():
    assert to_pascal("") == "Screen"


def test_to_constant_from_description():
    el = _elem(description="Login Field")
    assert to_constant(el) == "LOGIN_FIELD"


def test_to_constant_falls_back_to_text():
    el = _elem(text="Submit")
    assert to_constant(el) == "SUBMIT"


def test_to_constant_falls_back_to_name():
    el = _elem(name="username")
    assert to_constant(el) == "USERNAME"


def test_to_constant_falls_back_to_tag():
    el = _elem(tag="button")
    assert to_constant(el) == "BUTTON"


def test_to_var_name_max_30_chars():
    el = _elem(description="a" * 100)
    assert len(to_var_name(el)) <= 30


def test_dedup_name_first_occurrence_unchanged():
    seen: dict[str, int] = {}
    assert dedup_name("MONTANT", seen) == "MONTANT"


def test_dedup_name_appends_suffix():
    seen: dict[str, int] = {}
    assert dedup_name("VAR", seen) == "VAR"
    assert dedup_name("VAR", seen) == "VAR_2"
    assert dedup_name("VAR", seen) == "VAR_3"
    assert dedup_name("OTHER", seen) == "OTHER"
    assert dedup_name("VAR", seen) == "VAR_4"
