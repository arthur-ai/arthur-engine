"""Compiled block: block.dispatch -> tool:lookup_order -> block.render.

260/260 recorded renders match one format string; field transforms voted across all 260 windows. Replay over the baseline phase: coverage 100.0%, agreement 100.0%.
Eliminates 2 model calls per occurrence and preserves the lookup_order call.
"""

import re


_ARG_RX = re.compile(r"#(\d{3,})")
_TEMPLATE = 'Order {order_id} is {status} and arrives {eta}.'
_TOOL = 'lookup_order'
_FIELDS = {"status": "spaces", "eta": "identity", "order_id": "identity"}
_TRANSFORMS = {
    "identity": lambda v: str(v),
    "spaces": lambda v: str(v).replace("_", " "),
    "title": lambda v: str(v).replace("_", " ").title(),
    "upper": lambda v: str(v).upper(),
}


def guard(text):
    """Admit only inputs the argument extractor can actually read.

    The guard covers the *extraction*, not the whole block: the tool call in the
    middle is preserved, so what has to be safe is deriving its arguments.
    """
    return len(_ARG_RX.findall(text)) == 1


def block(text, call_tool):
    """Collapsed form of block.dispatch -> tool:lookup_order -> block.render.

    Two model calls become an extraction and a template render. The tool call
    between them is real work and is kept, which is why `call_tool` is injected
    rather than reimplemented.
    """
    m = _ARG_RX.search(text)
    if m is None:
        return None
    result = call_tool(_TOOL, {"order_id": m.group(1)})
    try:
        values = {k: _TRANSFORMS[t](result[k]) for k, t in _FIELDS.items()}
    except KeyError:
        return None
    return _TEMPLATE.format(**values)
