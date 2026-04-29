"""Pre-trained logistic-regression head for the claim filter.

The .pth file lives in this directory because it's coupled to the
claim_filter inference logic. `WEIGHTS_PATH` is the absolute path the
runtime loader (models/loader.py) reads via torch.load.
"""

import os

WEIGHTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "354ec0a465a14726b825b3bd5b97137b.pth",
)
