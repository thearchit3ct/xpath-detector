import json
from datetime import datetime

from xpath_detector.models import Element, Screen, Session, XPathCandidate


def test_xpathcandidate_immutable():
    candidate = XPathCandidate(strategy="by_id", expression="//input[@id='a']", stability_score=95)
    assert candidate.strategy == "by_id"
    assert candidate.stability_score == 95


def test_element_to_dict():
    element = Element(
        tag="input",
        text=None,
        attributes={"id": "login"},
        xpaths=[XPathCandidate("by_id", "//input[@id='login']", 95)],
        is_visible=True,
        is_enabled=True,
        description="Login field",
    )
    data = element.to_dict()
    assert data["tag"] == "input"
    assert data["attributes"]["id"] == "login"
    assert data["xpaths"][0]["strategy"] == "by_id"


def test_session_round_trip_json():
    session = Session(id="test_001", screens={})
    screen = Screen(
        name="login",
        url="https://x.fr",
        title="Login",
        timestamp=datetime(2026, 5, 12, 10, 0, 0),
        elements=[],
    )
    session.screens["login"] = screen

    data = session.to_dict()
    json_str = json.dumps(data)
    restored = Session.from_dict(json.loads(json_str))
    assert restored.id == "test_001"
    assert "login" in restored.screens
    assert restored.screens["login"].url == "https://x.fr"
