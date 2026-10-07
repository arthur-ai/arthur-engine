"""Whether a source's base_url is an address requests can send to.

Shared by the Jamf and Splunk connectors, whose own tests check only that they ask.
"""

import pytest

from discovery.address import address_problem


@pytest.mark.parametrize(
    "url",
    [
        "https://acme.example.com:abc",
        "https://acme.example.com:99999",
        "https://[acme.example.com",
        "https://",
        "https://acme example.com",
        "https://acme.example.com​",
        "https://.acme.example.com",
        "https://*.example.com",
        "https://acme.example.com%",
        # Passes requests' URL preparation; urllib3 refuses it only at connect time.
        "https://acme..example.com",
    ],
)
def test_an_address_requests_cannot_send_to_is_a_problem(url: str) -> None:
    """https, so each passes a connector's scheme check, but requests or urllib3 refuses
    every one with a ValueError rather than a transport error."""
    problem = address_problem(url)

    assert problem is not None and "not a valid address" in problem
    assert "acme" not in problem


@pytest.mark.parametrize(
    "url",
    [
        "https://user:hunter2@acme.example.com",
        "https://user:hunter2@acme.example.com:abc",
    ],
)
def test_credentials_in_the_address_are_a_problem_that_is_not_repeated(
    url: str,
) -> None:
    """requests turns URL userinfo into a Basic header that replaces the Bearer token, so
    every call would 401. base_url is outside the scrub set, so the answer must not
    repeat it."""
    problem = address_problem(url)

    assert problem is not None
    assert "hunter2" not in problem and "user:" not in problem


@pytest.mark.parametrize(
    "url",
    [
        "https://acme.example.com",
        "https://acme.example.com:8443/",
        "https://acme.example.com.",
        "https://10.0.0.5:8089",
        "https://[::1]:8089",
    ],
)
def test_a_usable_address_is_not_a_problem(url: str) -> None:
    assert address_problem(url) is None
