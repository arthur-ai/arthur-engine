"""GLiNER tokenizer config for PII v2.

The JSON config travels with the PII inference module (mirroring
genai-engine's scorer/checks/pii/gliner/ layout). `CONFIG_PATH` is the
absolute path the runtime loader passes to `GLiNERConfig.from_json_file`.
"""

import os

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "gliner_tokenizer_config.json",
)
