"""Upstream `ai-detection-spec`, vendored at the ref named in VERSION.

`classify.py` is `bin/classify` verbatim -- the spec's reference matcher, held upstream to
its conformance vectors, which is why it is copied rather than reimplemented: a second
matcher here would be held to nothing. `vectors.json` is those vectors, and this engine's
tests hold its own matcher to them too.

`catalog.json` is the FLOOR, not the source of truth: the catalog document the release
attaches. A Discovery Source Config carries the catalog that actually runs, so a new
signature is a config change rather than an image rebuild; this is what an unconfigured
source falls back to. `catalog.schema.json` validates every catalog document before it is
read, and `evidence.schema.json` is the row contract the envelope reads by.

Do not edit any of them by hand -- re-vendor.
"""
