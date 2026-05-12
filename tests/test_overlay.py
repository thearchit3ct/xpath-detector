from xpath_detector.overlay import OVERLAY_JS


def test_overlay_js_is_non_empty():
    assert len(OVERLAY_JS) > 100


def test_overlay_js_contains_capture_marker():
    assert "__XPATH_CAPTURE__" in OVERLAY_JS


def test_overlay_js_listens_to_ctrl_click():
    assert "ctrlKey" in OVERLAY_JS or "metaKey" in OVERLAY_JS


def test_overlay_click_uses_elementfrompoint():
    """Click handler must use document.elementFromPoint for consistency with hover."""
    from xpath_detector.overlay import OVERLAY_JS
    click_block = OVERLAY_JS[OVERLAY_JS.find("'click'"):OVERLAY_JS.find("'keydown'")]
    assert "elementFromPoint" in click_block, "click handler should use elementFromPoint"


def test_overlay_has_find_nearby_label():
    from xpath_detector.overlay import OVERLAY_JS

    assert "findNearbyLabel" in OVERLAY_JS
    assert "nearby_label" in OVERLAY_JS


def test_overlay_uses_label_for_attribute():
    from xpath_detector.overlay import OVERLAY_JS

    assert 'label[for="' in OVERLAY_JS or "label[for=" in OVERLAY_JS
