"""
Getting started: send one trace to Arthur.

Install dependencies:
    pip install -r tutorials/requirements.txt

Fill in the values below, then run:
    python tutorials/getting_started.py
"""

import openai

from arthur_observability_sdk import Arthur

# ── Configure these ────────────────────────────────────────────────────────────
ARTHUR_BASE_URL = "http://localhost:3030"   # Arthur GenAI Engine URL
ARTHUR_API_KEY = "your-arthur-api-key"
# ARTHUR_TASK_ID = "your-task-id" # Optional, will be created if not provided

OPENAI_API_KEY = "your-openai-api-key"
# ───────────────────────────────────────────────────────────────────────────────

arthur = Arthur(
    api_key=ARTHUR_API_KEY,
    base_url=ARTHUR_BASE_URL,
    task_id=ARTHUR_TASK_ID,
    service_name="getting-started",
)
arthur.instrument_openai()

client = openai.OpenAI(api_key=OPENAI_API_KEY)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
)

print(response.choices[0].message.content)

arthur.shutdown()
