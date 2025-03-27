<div align="center">

# The Arthur Engine

<i>Make AI work for Everyone.</i>

[![GenAI Engine CI](https://github.com/arthur-ai/arthur-engine-temp/actions/workflows/genai-engine-workflow.yml/badge.svg)](actions?query=workflow%3A%22%22GenAI+Engine+Workflow%22%22++)
[![Discord](https://img.shields.io/badge/Discord-Arthur-blue?logo=discord&logoColor=white)](https://discord.gg/tdfUAtaVHz)

[Website](https://arthur.ai) - [Documentation](https://shield.docs.arthur.ai/docs) - [Talk to someone at Arthur](https://www.arthur.ai/arthur-book-a-demo)

</div>

The Arthur Engine is a tool designed for:

- **Evaluating and Benchmarking Machine Learning models**
  - Support for a wide range of evaluation metrics (e.g., drift, accuracy, precision, recall, F1, and AUC)
  - Tools for comparing models, exploring feature importance, and identifying areas for optimization
  - For LLMs/GenAI applications, measure and monitor response relevance, hallucination rates, token counts, latency, and more
- **Enforcing guardrails in your LLM Applications and Generative AI Workflows**
  - Configurable metrics for real-time detection of PII or Sensitive Data leakage, Hallucination, Prompt Injection attempts, Toxic language, and other quality metrics
- **Extensibility to fit into your application's architecture**
  - Support for plug-and-play metrics and extensible API so you can bring your own custom-models or popular open-source models (inc. HuggingFace, etc.)

## Quickstart

1. Clone the repository and `cd genai-engine/docker-compose`
2. Copy `*.env.template` files and modify them (more instructions can be found in README on the current path)
3. Run `docker compose up`
4. Wait for the `genai-engine` container to initialize then navigate to localhost:3000/docs to see the API docs
5. Start building!

## Arthur Platform Enterprise Version

The Arthur Engine provides a **complete service** for monitoring and governing your AI/ML workloads using popular Open-Source technologies and frameworks (see below for further details).

**The enterprise version of the Arthur Platform provides better performance, additional features, and capabilities**, including custom enterprise-ready guardrails + metrics, which can maximize the potential of AI for your organization.

Key features:

- State-of-the-art proprietary evaluation models trained by Arthur's world-class machine learning engineering team
- Airgapped deployment of the Arthur Engine (no dependency to Hugging Face Hub)
- Optional on-premises deployment of the entire Arthur Platform
- Support from the world-class engineering teams at Arthur

To learn more about the enterprise version of the Arthur Platform, [reach out!](https://www.arthur.ai/arthur-book-a-demo)

Performance Comparison between Free vs Enterprise version of Arthur Engine :

Enterprise version of Arthur Engine leverages state-of-the-art high-performing, low latency proprietary models for some of the LLM evaluations. Please see below for a detailed comparison between open-source vs enterprise performance.
| **Evaluation Type**  | **Dataset**                     | **Free Version Performance (f1)** | **Enterprise Performance (f1)** | **Free Version Average Latency per Inference (s)** | **Enterprise Average Latency per Inference (s)** |
|----------------------|--------------------------------|----------------------------------|--------------------------------|-------------------------------------------------|--------------------------------------------------|
| Prompt Injection    | deepset                        | 0.52 (0.44, 0.60)               | 0.89 (0.85, 0.93)              | 0.966                                           | 0.03                                             |
| Prompt Injection    | Arthur’s Custom Benchmark      | 0.79 (0.62, 0.93)               | 0.85 (0.71, 0.96)              | 0.16                                            | 0.005                                            |
| Toxicity           | Arthur’s Custom Benchmark      | 0.633 (0.45, 0.79)              | 0.89 (0.85, 0.93)              | 3.096                                           | 0.0358                                           |




**The free version of Arthur Platform is coming soon!**

If you are interested in joining the waitlist or learning more, [send us a note]([https://www.arthur.ai/waitlist])

![Arthur GenAI Evals](./docs/images/arthur-genai.png)

## Overview

The Arthur Engine is built with a focus on transparency and explainability, this framework provides users with comprehensive performance metrics, error analysis, and interpretable results to improve model understanding and outcomes.
With support for plug-and-play metrics and extensible APIs, the Arthur Engine simplifies the process of understanding and optimizing generative AI outputs.
The Arthur Engine can prevent data-security and compliance risks from creating negative or harmful experiences for your users in production or negatively impacting your organization's reputation.

**Key Features:**

- Evaluate models on structured/tabular datasets with customizable metrics
- Evaluate LLMs and generative AI workflows with customizable metrics
- Support building real-time guardrails for LLM applications and agentic workflows
- Trace and monitor model performance over time
- Visualize feature importance and error breakdowns
- Compare multiple models side-by-side
- Extensible APIs for custom metric development or for using custom models
- Integration with popular libraries like LangChain or LlamaIndex (coming soon!)

**LLM Evaluations:**

| Eval                                | Technique                                                                                                         | Source                                                                        | Docs                                                        |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Hallucination                       | Claim-based LLMJudge technique                                                                                    | [Source](genai-engine/genai_engine/scorer/checks/hallucination/v2.py)               | [Docs](https://shield.docs.arthur.ai/docs/hallucination)    |
| Prompt Injection                    | Open Source: Using [deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) | [Source](genai-engine/genai_engine/scorer/checks/prompt_injection/classifier.py)    | [Docs](https://shield.docs.arthur.ai/docs/prompt-injection) |
| Toxicity                            | Open Source: Using [roberta_toxicity_classifier](https://huggingface.co/s-nlp/roberta_toxicity_classifier)                     | [Source](genai-engine/genai_engine/scorer/checks/toxicity/toxicity.py)              | [Docs](https://shield.docs.arthur.ai/docs/toxicity)         |
| Sensitive Data                      | Few-shot optimized LLM Judge technique                                                                             | [Source](genai-engine/genai_engine/scorer/checks/sensitive_data/custom_examples.py) | [Docs](https://shield.docs.arthur.ai/docs/sensitive-data)   |
| Personally Identifiable Information | Using [presidio](https://github.com/microsoft/presidio) based off Named-Entity recognition                        | [Source](genai-engine/genai_engine/scorer/checks/pii/classifier.py)                 | [Docs](https://shield.docs.arthur.ai/docs/pii-leakage)      |
| CustomRules                         | Extend the service to support whatever monitoring or guardrails are applicable for your use-case                  | Build your own!                                                               | [Docs](https://shield.docs.arthur.ai/docs/custom-rules)     |

_NB: We have provided open-source models for Prompt Injection and Toxicity evaluation as default in the free version of Arthur. In the case that you already have custom solutions for these evaluations and would like to use them, the models used for Prompt Injection and Toxicity are fully customizable and can be substituted out here ([PI Code Pointer](genai-engine/genai_engine/scorer/checks/prompt_injection/classifier.py#L20), [Toxicity Code Pointer](genai-engine/genai_engine/scorer/checks/toxicity/toxicity.py#L29)). If you are interested in higher performing and/or lower latency evaluations out of the box, please enquire about the enterprise version of Arthur Engine._
### Deploying the stand-alone Guardrails

The Arthur Engine can be deployed as **a stand-alone capability for building real-time guardrails for your LLM applications and agentic workflows**. Read about the guardrails capability (also formerly known as Arthur Shield) [here](https://shield.docs.arthur.ai).

The guardrails capability requires the deployment of the GenAI Engine. Follow the `genai-engine` deployment instructions [here](genai-engine/README.md).

### Deploying the full capabilities of the Arthur Engine with the Arthur Platform

To use the Arthur Engine's full capabilities, log in to the [Arthur Platform](https://platform.arthur.ai) and follow the instructions.

## Contributing

- Join the Arthur community on [Discord](https://discord.gg/tdfUAtaVHz) to get help and share your feedback.
- For bug fixes and feature requests, please file a Github issue.
