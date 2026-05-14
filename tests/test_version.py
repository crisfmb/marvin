from marvin.version import get_version


def test_get_version_returns_expected_value() -> None:
    assert get_version() == "0.1.0"
