"""Upstream `osquery-ai-discovery`, vendored at the ref named in VERSION.

`classify.py` is `bin/classify` verbatim -- the reference matcher, and upstream's own
docstring is the reason it is copied rather than reimplemented: "if you want to know
what a signature means, this is the answer, and any other implementation that disagrees
with it is wrong."

`agents.yaml` and `routes.yaml` are the FLOOR, not the source of truth. A Discovery
Source Config carries the catalog that actually runs, so a new signature is a config
change rather than an image rebuild; these are what an unconfigured source falls back
to. Do not edit any of the four by hand -- re-vendor.
"""
