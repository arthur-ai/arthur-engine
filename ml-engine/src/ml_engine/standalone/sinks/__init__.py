"""Where a standalone engine sends what it discovers: its sink targets.

- `common`: what every target shares -- the events it is handed, the `Sink` API it
  implements, and the error it raises.
- `http`: the base for targets that deliver over HTTP, with batching, retries and
  scrubbing already done.
- `record_sink`: `StandaloneRecordSink`, which the scan loop publishes through whatever
  the target.
- One module per target, under the family it belongs to (`siem.splunk_hec`), or at the
  top level when it has none (`webhook`). Each holds the target's config model, whose
  `build_sink` makes its `Sink`, and nothing else.

ADDING A TARGET is a module holding its config model and its sink, and one entry in
`Destination` below. `Destination` is the one list of targets, as
`discovery.source_connectors` is of connectors: the config file's `destination` is
validated against it, keyed on each model's `type`.
"""

from typing import Annotated, Union

from pydantic import Field

from standalone.sinks.siem.splunk_hec import SplunkHecDestination
from standalone.sinks.webhook import WebhookDestination

Destination = Annotated[
    Union[SplunkHecDestination, WebhookDestination],
    Field(discriminator="type"),
]
