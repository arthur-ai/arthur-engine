import pytest

from scorer.checks.pii.validations import is_url


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/path",
        "example.com:8080/path",
        "https://john@example.com",
        "https://user:pass@db.example.com/x",
        "https://admin:hunter2@db.example.com:5432/app",
        "http://[2001:db8::1]:8080/",
        "http://192.168.0.1:8080/x",
    ],
)
def test_is_url_accepts_urls(value: str):
    assert is_url(value)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "value",
    [
        "192.168.0.1",
        "not a url",
        "https://localhost",
        "https://user:pass@localhost/x",
        "ssh://example.com",
    ],
)
def test_is_url_rejects_non_urls(value: str):
    assert not is_url(value)
