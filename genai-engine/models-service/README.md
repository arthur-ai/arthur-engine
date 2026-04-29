# Arthur Models Service

Sideloaded torch/transformers inference service for the GenAI Engine scorer checks.

Hosts the ML models that previously ran in-process inside `genai-engine`:
- Prompt injection (DebertaV3)
- Toxicity (RoBERTa + ONNX profanity)
- PII (GLiNER + Presidio + spaCy, with v1 Presidio-only fallback)
- Hallucination claim filter (sentence-transformers + local logreg)

The LLM judge for hallucination and the LLM-based `sensitive_data` check stay in `genai-engine`.

See module docstrings under `src/inference/<check>/classifier.py` for each endpoint's API contract and behavior.

## Run locally

```bash
uv sync
export MODEL_REGISTRY_SECRET=...
export MODEL_STORAGE_PATH=./models  # or omit to use HF cache
uv run serve
```

## API

All endpoints under `/v1`. All require `Authorization: Bearer $MODEL_REGISTRY_SECRET` except `/v1/health`.

| Path | Purpose |
|---|---|
| `GET /v1/health` | Liveness (no auth) |
| `GET /v1/ready` | Readiness — true once models are warm |
| `GET /v1/models` | Loaded models, devices, revisions |
| `POST /v1/inference/prompt_injection` | Per-chunk INJECTION/SAFE classification |
| `POST /v1/inference/toxicity` | Aggregate toxicity score + violation type |
| `POST /v1/inference/pii` | Entity spans (GLiNER+Presidio+spaCy or Presidio-only) |
| `POST /v1/inference/claim_filter` | CLAIM/NONCLAIM/DIALOG classification |
