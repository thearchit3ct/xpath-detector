from xpath_detector.shell import parse_command


def test_parse_simple_command():
    assert parse_command("list") == ("list", [])


def test_parse_command_with_args():
    assert parse_command("open https://x.fr") == ("open", ["https://x.fr"])


def test_parse_command_strips_whitespace():
    assert parse_command("  list  ") == ("list", [])


def test_parse_empty_returns_empty_command():
    assert parse_command("") == ("", [])
