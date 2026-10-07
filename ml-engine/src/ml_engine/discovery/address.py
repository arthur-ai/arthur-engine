"""Whether a source's URL is an address requests can send to.

For connectors that take the vendor's URL as a source field (base_url,
elasticsearch_url). One that is https but has a bad port or host passes the scheme
check and then fails inside requests, as a ValueError rather than a transport error,
so a scheduled scan reads it as the vendor failing instead of the source's settings.
Used by the Jamf, Splunk and Elastic connectors.
"""

from typing import Optional
from urllib.parse import urlsplit

from requests.models import PreparedRequest


def address_problem(url: str) -> Optional[str]:
    """What is wrong with `url` as an address to send to, or None.

    Checked with the code that will send to it rather than a second parser, which would
    disagree with it somewhere: requests' URL preparation, then the IDNA encoding urllib3
    applies to the host only when it opens the connection (an empty label passes the
    first and fails the second).

    The answer names the problem and never repeats `url`: the URL field is outside the
    scrub set, so a URL with a password in it would put that password in the job log.
    """
    try:
        PreparedRequest().prepare_url(url, None)
        parts = urlsplit(url)
        (parts.hostname or "").encode("idna")
    except ValueError:  # InvalidURL, LocationParseError and UnicodeError all are
        return "is not a valid address: its host or port cannot be parsed"
    if parts.username is not None or parts.password is not None:
        # requests turns URL userinfo into a Basic Authorization header that replaces the
        # connector's own token, so the scan would run as that user, or 401 and read as
        # the credentials failing.
        return "must not contain a username or password"
    return None
