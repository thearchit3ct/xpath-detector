from xpath_detector.overlay import OVERLAY_JS


def test_overlay_js_is_non_empty():
    assert len(OVERLAY_JS) > 100


def test_overlay_js_contains_capture_marker():
    assert "__XPATH_CAPTURE__" in OVERLAY_JS


def test_overlay_js_listens_to_ctrl_click():
    assert "ctrlKey" in OVERLAY_JS or "metaKey" in OVERLAY_JS
