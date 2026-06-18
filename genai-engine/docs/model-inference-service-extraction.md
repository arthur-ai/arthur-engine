# Model Inference Service — Extraction Strategy

> Migrated from Notion ([original page](https://www.notion.so/arthurai/Model-Inference-Service-Extraction-Strategy-3821d37e9a108079aa7acfe96e6c4d69)) on 2026-06-18. Review comments left on the original page have been carried over as inline comments on this PR.

## Context

The genai-engine today runs as a monolith: CRUD endpoints, guardrail rule evaluation, and local ML model inference all in one process on a GPU instance. This document covers the strategy for extracting the ML inference layer into a standalone **Model Inference Service** (MIS).

**What moves out:** The six HuggingFace classifier/embedding models loaded in `utils/model_load.py`, plus the Arthur-trained claim classifier:

- `deberta-v3-base-prompt-injection-v2` (prompt injection)
- `roberta_toxicity_classifier` (toxicity)
- `gliner_multi_pii-v1` (PII entity extraction)
- `all-MiniLM-L12-v2` (embeddings — used by hallucination v1 **and** the v2 claim classifier)
- `deberta-v2-xlarge-mnli` (relevance)
- `pardonmyai` (profanity)
- `claim_classifier` (Arthur-trained logistic-regression head over `all-MiniLM-L12-v2` embeddings; labels hallucination v2 chunks CLAIM / NONCLAIM / DIALOG). Today this `.pth` is committed in the engine repo and shipped in the image — it is **not** one of the HuggingFace six and is not yet in `models-manifest.json`. It moves to MIS as a named model (`claim_classifier`) and must be added to the manifest. Hosting the full embedding+head in MIS keeps the engine model-free and avoids shipping raw embedding vectors over the wire on every chunk.

**What stays in the engine:** Model provider configs (OpenAI/Vertex/Bedrock credentials), CRUD endpoints, rule management, inference record storage, LLM-based guardrail judgments (e.g. hallucination v2's claim-validation LLM calls), and claim *chunking* (`utils/claim_parser.py` — commonmark + NLTK sentence tokenization, no model). Note: hallucination v2 is **not** LLM-only — it calls MIS for embeddings and claim classification *before* the LLM judgment step.

**Weight distribution:** MIS does not bake weights into its image. It reuses the existing `deployment/model-upload/` subsystem — models are pre-downloaded and served from S3 / GCS / PVC / EFS and mounted into the service, pinned by `models-manifest.json` (per-model commit hashes + combined hash). This is the same mount mechanism customers already use to share weights across their engines today, and it is preserved unchanged.

**Primary motivations:**

- One GPU deployment serves N engine deployments → eliminates per-deployment GPU cost in SaaS
- Engine becomes CPU-only → smaller image, no model download at startup (10min → ~0)
- Model lifecycle (updates, versioning) decoupled from engine releases

---

## 1. Model Inference Service API

### Endpoint Design

Single unified inference endpoint. Model name in the payload routes to the correct loaded model.

```plain text
POST /infer
```

**Request:**

```json
{
  "model": "pii",
  "text": "Call me at 555-867-5309",
  "config": {}
}
```

**Response envelope:**

```json
{
  "model": "pii",
  "result_type": "entities",
  "result": [
    { "entity": "PHONE_NUMBER", "start": 10, "end": 22, "score": 0.97 }
  ],
  "latency_ms": 18
}
```

Result types per model:

| Model | result_type | result shape |
|---|---|---|
| prompt_injection | score | `{ "score": float, "label": "INJECTION" \| "SAFE" }` |
| toxicity | score | `{ "score": float, "label": "toxic" \| "non-toxic" }` |
| pii | entities | `[{ "entity": str, "start": int, "end": int, "score": float }]` |
| embeddings | vector | `{ "embedding": [float, ...] }` |
| claim_classifier | label | `{ "label": "CLAIM" \| "NONCLAIM" \| "DIALOG", "score": float }` |
| relevance | score | `{ "score": float }` |
| profanity | score | `{ "score": float, "label": "profane" \| "clean" }` |

**Health:**

```plain text
GET /health        → { "status": "ok", "models_loaded": [...] }
GET /models        → list of available model names + metadata
```

### Parallelism Model

Two levels of parallelism, both already present in the engine today:

**Engine side (unchanged):** `scorer/score.py` fans out guardrail checks via thread pool. Each check becomes a parallel HTTP POST to the MIS instead of a local function call. No changes needed to the parallelism logic — just swap the transport.

**MIS side:** Each model is loaded once into memory at startup. The serving framework handles concurrent inference requests. For GPU: requests to the same model batch automatically. For CPU: thread-pool workers per model.

Target latency per inference call to MIS: **20–80ms** (local network). Parallel fan-out means wall time is bounded by the slowest single model, not the sum.

### Off-the-Shelf Options (OSS)

**Recommended: FastAPI (custom, same stack as engine)**

Lowest friction. Team already owns the stack. Models loaded as module-level singletons, same pattern as `model_load.py` today. Uvicorn handles concurrency. Add a thread-pool executor for CPU-bound inference to avoid blocking the event loop.

Tradeoffs: no automatic batching, manual concurrency tuning required. Sufficient for initial version.

**BentoML**

Purpose-built for exactly this use case. Native HuggingFace support, handles model loading, batching, and serving out of the box. Better packaging story (models + code bundled as a Bento). Adds a dependency and abstraction layer the team needs to learn.

Good choice if you want built-in dynamic batching and a cleaner model versioning story without Triton's complexity.

**Triton Inference Server (NVIDIA)**

Most production-grade option. Dynamic batching, multi-GPU, ONNX/TensorRT support, Prometheus metrics built in. Significant operational complexity — models need to be converted to Triton-compatible formats (ONNX or TorchScript). Overkill for six small classifiers but the right long-term answer if GPU utilization optimization becomes critical.

**TorchServe**

PyTorch-native, supports batch inference, has a model store concept. Middle ground between FastAPI and Triton. Less community momentum than BentoML currently.

**Recommendation:** Start with FastAPI (fast to ship, zero new dependencies). Migrate to BentoML when you need proper model versioning and batching. Triton only if GPU throughput becomes a bottleneck.

---

## 2. Deployment Strategy

### a. Self-Hosted

Two sub-cases, same underlying mechanism.

**Docker pull/run (OSS, no Arthur connection):**

Users run two containers. The engine image is now CPU-only and ships without model weights (~500MB vs. ~8GB today). The MIS image ships code only; weights are mounted at runtime from the existing `model-upload` distribution (S3/GCS/PVC/EFS), so there is no runtime HuggingFace download and no fat image to ship.

```bash
# Model inference service (GPU). Weights mounted from the shared models volume.
docker run -d --gpus all \
  -p 8001:8001 \
  -v /path/to/models:/models \
  -e MODELS_DIR=/models \
  arthur/model-inference-service:latest

# Engine (CPU)
docker run -d \
  -e MODEL_SERVICE_URL=http://localhost:8001 \
  -e POSTGRES_URL=... \
  -p 8000:8000 \
  arthur/genai-engine:latest
```

Provide a `docker-compose.yml` for users who want one command. GPU passthrough via Compose `devices` config.

**Bash script (connected to Arthur platform):**

Two modes controlled by a flag:

```bash
# Default: use Arthur-hosted MIS (inference text leaves customer network)
bash <(curl -sSL https://engine.arthur.ai) \
  --arthur-client-id=<id> \
  --arthur-client-secret=<secret> \
  --arthur-api-host=<host>

# Private inference: run MIS locally (all data stays on-prem)
bash <(curl -sSL https://engine.arthur.ai) \
  --arthur-client-id=<id> \
  --arthur-client-secret=<secret> \
  --arthur-api-host=<host> \
  --private-inference
```

Without `--private-inference`: script starts only the engine container, sets `MODEL_SERVICE_URL` to Arthur's hosted MIS endpoint. No GPU required on the customer machine.

With `--private-inference`: script pulls and starts both containers locally, wires `MODEL_SERVICE_URL` to localhost automatically. GPU required.

### b. On-Prem (CFT / Helm)

**CFT (ECS):**

Two separate ECS services. Engine service uses CPU task definition only — the GPU task definition is eliminated from the engine and moves to MIS.

- MIS: GPU ECS service, internal ALB, min 1 task (never scale to zero — cold start on GPU is 30–60s)
- Engine: CPU ECS service, scales horizontally via ECS scaling policies
- Routing: engine resolves MIS via internal ALB DNS, no public exposure
- Auth: IAM task roles — engine task role gets `execute-api:Invoke` on MIS ALB

**Helm (K8s):**

MIS runs as a `Deployment` with GPU node affinity and tolerations. Engine runs as a standard `Deployment` with HPA. The current daemonset/deployment split in `values.yaml.template` simplifies — engine is always a standard Deployment, GPU concerns are MIS-only.

```yaml
# MIS
nodeSelector:
  nvidia.com/gpu: "true"
tolerations:
  - key: nvidia.com/gpu
    operator: Exists
resources:
  limits:
    nvidia.com/gpu: "1"

# Engine
# No GPU constraints. HPA on CPU/request metrics.
```

MIS exposed as ClusterIP service (internal only). Engine resolves via cluster DNS.

### c. SaaS Multi-Tenant

Arthur hosts one MIS deployment (or a small number by region). N engine deployments — either per-tenant or shared multi-tenant engines — all route to the same MIS.

MIS is stateless compute only. No tenant context stored. Engine passes inference text, receives scores, handles all persistence and tenancy logic itself.

Auth between engine and MIS: reuse the existing shared-secret pattern already in the codebase. Today `ml-engine` authenticates to `genai-engine` via `GENAI_ENGINE_INTERNAL_API_KEY` (matched against the engine's admin key), wired through docker-compose, CloudFormation, and Helm secrets. MIS adopts the same model — a shared internal secret injected via the existing secrets path. Per-tenant token scoping is explicitly out of scope for now: MIS holds no tenant context, so a single shared secret per MIS deployment is sufficient. (mTLS or a token-issuing service can be revisited later if MIS ever needs to attribute or rate-limit per tenant.)

This is the primary cost driver for the extraction: GPU capacity shared across all tenants rather than provisioned per deployment.

### d. Vertex AI

Vertex is a first-class supported MIS deployment target. Deploy the MIS as a Vertex AI custom prediction container: model artifacts come from the same `model-upload` GCS backend already used today, served via a Vertex endpoint. Engine calls the Vertex endpoint URL via `MODEL_SERVICE_URL` instead of a self-hosted MIS — the engine is agnostic to where MIS runs.

Note: this is a different integration from the existing Vertex-as-LLM-provider config (GCP project ID + service-account creds in `values.yaml.template`), which lets the engine use a Vertex GPT model as an LLM provider. MIS-on-Vertex serves Arthur's own classifier/embedding models and should not reuse that provider config path.

User journey:
1. Model artifacts published to GCS via the existing `model-upload` GCS job
2. Vertex endpoint created/updated from the MIS custom container
3. Engine configured with `MODEL_SERVICE_URL=https://<region>-aiplatform.googleapis.com/...`
4. Vertex handles GPU provisioning, autoscaling, and availability SLAs

Benefits: no GPU ops burden, Vertex committed use discounts, automatic scaling, Google's availability SLA. Usable both as an Arthur-hosted SaaS option and by GCP-native customers who want to run MIS in their own project.

Constraints: inference text flows to Google's infrastructure — requires GCP DPA and may not be acceptable for customers with strict data residency requirements outside GCP. Vertex endpoints are region-specific; multi-region adds deployment complexity.

---

## 3. Data Governance

The central question in every deployment case: **does inference text (customer prompts and responses) leave the customer's control boundary?**

The MIS is a pass-through compute service — it receives text, runs inference, returns scores. It must not persist inference text at any layer. This is a hard implementation requirement and should be enforced by design (no logging of request bodies, no DB writes in MIS).

### Self-Hosted, Private (`--private-inference` or docker run)

Text never leaves the customer's machine. Engine and MIS run on the same host or same private network. Arthur has zero visibility into inference content. Audit logs (if any) are local. **Full data residency.**

### Self-Hosted, Connected (default bash script mode, no `--private-inference`)

Text travels from the customer's network to Arthur's hosted MIS over HTTPS. This must be disclosed explicitly during onboarding — ideally at `--arthur-api-host` registration, not buried in docs. MIS must not log request bodies. Engine continues to own all inference record storage. **Data leaves customer network — requires explicit opt-in and DPA coverage.**

### On-Prem CFT / Helm (customer deploys both engine and MIS in their own infra)

Customer runs MIS inside their own AWS account or K8s cluster. Text never leaves their VPC. Arthur does not have access to the MIS or its logs. This is operationally equivalent to self-hosted from a data governance standpoint. **Full data residency.**

The CFT and Helm templates should support this cleanly — customer deploys the full stack themselves, Arthur provides the templates and images only.

### SaaS Multi-Tenant (Arthur hosts everything)

Standard SaaS data processing. Inference text flows through Arthur-managed infrastructure end to end. Covered by Arthur's DPA and standard data processing terms. MIS must enforce no persistence of inference content. Audit logging lives in the engine layer, not MIS.

Consider: regional MIS deployments (US, EU) to support data residency requirements without customers needing to self-host.

### Vertex AI

Inference text flows to Google Cloud. Google's data processing terms apply in addition to Arthur's. Requires a GCP BAA if any inference text could be considered health data. Not suitable for customers with strict non-GCP data residency requirements.

Supported both as an Arthur-hosted SaaS option and as a customer-run target for GCP-native customers; in either case the GCP data-processing terms above apply.

---

## Summary Matrix

| Deployment | Who runs MIS | Text leaves customer | GPU ops owner | DPA requirement |
|---|---|---|---|---|
| Self-hosted, private | Customer (local) | No | Customer | None |
| Self-hosted, connected | Arthur (hosted) | Yes | Arthur | Arthur ↔︎ Customer |
| On-prem CFT/Helm | Customer (their cloud) | No | Customer | None |
| SaaS multi-tenant | Arthur | Yes (Arthur infra) | Arthur | Arthur ↔︎ Customer |
| Vertex AI | Google (via Arthur) | Yes (GCP) | Google/Arthur | Arthur + GCP DPA |

---

## Open Items

- Decide default mode for bash script (Arthur-hosted MIS vs. `--private-inference`). Recommendation: default to private, Arthur-hosted as opt-in with explicit disclosure.
- Define circuit breaker behavior in the engine when MIS is unreachable: fail-open (skip ML checks, pass the inference) vs. fail-closed (block). Likely differs by rule type — fail-open on toxicity, fail-closed on PII.
- ~~Fat image strategy~~ **Resolved:** weights are mounted from the existing `model-upload` distribution (S3/GCS/PVC/EFS), not baked into the image. Preserves the volume-mount route customers already use to share weights across engines.
- Model versioning: `models-manifest.json` already pins per-model commits + a combined hash, so the versioning primitive exists. Still open: how MIS rolls a model update without downtime for connected engines. Minimum: blue/green at the service level.
