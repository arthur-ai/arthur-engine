"""The MDM-neutral half of endpoint discovery.

An endpoint agent writes one `arthur1.` string per device; an MDM carries it as a custom
attribute and hands it back over that vendor's API. Everything about the string -- the
frame, the six-column rows, what a scan row means -- is the same whichever MDM carried
it, so it lives here and each MDM package holds only its own API.
"""
