# Frontend Routes

All routes are defined in `src/App.tsx`. Task-scoped routes live under `/tasks/:id` and share the `TaskLayout` shell (sidebar nav, task context). Routes marked **redirect** forward to another path and render no page of their own.

---

## Public Routes

| Path     | Component   | Description                                                                     |
| -------- | ----------- | ------------------------------------------------------------------------------- |
| `/login` | `LoginPage` | Authentication page. Handles user login before accessing any protected content. |

---

## Global / Settings Routes

These routes are outside any task context and apply org-wide.

| Path                        | Component                               | Description                                                             |
| --------------------------- | --------------------------------------- | ----------------------------------------------------------------------- |
| `/`                         | `AllTasks`                              | Home page. Lists all tasks (LLM applications) the user has access to.   |
| `/settings/model-providers` | `ModelProviders` (in `SettingsPage`)    | Manage LLM model provider configurations (e.g., OpenAI, Azure OpenAI).  |
| `/settings/api-keys`        | `ApiKeysManagement` (in `SettingsPage`) | Create and manage API keys for authenticating against the GenAI Engine. |
| `*`                         | —                                       | Catch-all redirect → `/`                                                |

---

## Task-Scoped Routes (`/tasks/:id/...`)

All routes below are nested under `/tasks/:id` and rendered inside `TaskLayout`. `:id` is the task (application) identifier.

### Overview & Configuration

| Path                                                        | Component               | Description                                                                       |
| ----------------------------------------------------------- | ----------------------- | --------------------------------------------------------------------------------- |
| `/tasks/:id`                                                | —                       | Redirect → `overview`                                                             |
| `/tasks/:id/overview`                                       | `TaskOverview`          | Summary dashboard for a task: status, metrics, and quick-access links.            |
| `/tasks/:id/model-providers`                                | —                       | Redirect → `/settings/model-providers`                                            |
| `/tasks/:id/api-keys`                                       | —                       | Redirect → `/settings/api-keys`                                                   |
| `/tasks/:id/application-config`                             | —                       | Redirect → `/` (deprecated)                                                       |
| `/tasks/:id/rag-configurations`                             | `RagConfigurationsPage` | List and manage RAG (Retrieval-Augmented Generation) configurations for the task. |
| `/tasks/:id/rag-configurations/:configId`                   | `RagConfigurationsPage` | View/edit a specific RAG configuration.                                           |
| `/tasks/:id/rag-configurations/:configId/versions/:version` | `RagConfigurationsPage` | View a specific version of a RAG configuration.                                   |

### Testing & Experiments

| Path                                         | Component               | Description                                                                                     |
| -------------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------- |
| `/tasks/:id/test`                            | `TestView`              | Unified testing hub. Tabbed view containing agent experiments and agentic notebooks sections.   |
| `/tasks/:id/agent-experiments`               | —                       | Redirect → `../test?section=agent-experiments` (legacy URL)                                     |
| `/tasks/:id/agent-experiments/new`           | `NewAgentExperiment`    | Form to create a new agent experiment (define endpoints, test cases, eval config).              |
| `/tasks/:id/agent-experiments/:experimentId` | `AgentExperimentDetail` | Detail view for a single agent experiment: progress summary, test case results, HTTP templates. |
| `/tasks/:id/agentic-notebooks`               | —                       | Redirect → `../test?section=agentic-notebooks` (legacy URL)                                     |
| `/tasks/:id/agentic-notebooks/:notebookId`   | `AgentNotebookDetail`   | Interactive notebook for running and iterating on agentic workflows step-by-step.               |

### Datasets & Transforms

| Path                                         | Component                | Description                                                             |
| -------------------------------------------- | ------------------------ | ----------------------------------------------------------------------- |
| `/tasks/:id/datasets`                        | `DatasetsView`           | Browse and manage datasets associated with the task.                    |
| `/tasks/:id/datasets/:datasetId`             | `DatasetDetailView`      | View dataset contents, schema, and columns; supports row-level editing. |
| `/tasks/:id/datasets/:datasetId/experiments` | `DatasetExperimentsView` | List experiments that reference a specific dataset.                     |
| `/tasks/:id/transforms`                      | `TransformsManagement`   | Create and manage data transform pipelines applied to datasets.         |

### Evaluation

| Path                                                     | Component        | Description                                                                         |
| -------------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------- |
| `/tasks/:id/evaluate`                                    | `EvaluateView`   | Unified evaluation hub. Manages evaluators and continuous evaluations in one place. |
| `/tasks/:id/evaluators`                                  | —                | Redirect → `../evaluate` (legacy URL)                                               |
| `/tasks/:id/evaluators/:evaluatorName`                   | `Evaluators`     | Configure a specific evaluator (e.g., hallucination, toxicity, PII).                |
| `/tasks/:id/evaluators/:evaluatorName/versions/:version` | `Evaluators`     | View a specific version of an evaluator's configuration.                            |
| `/tasks/:id/continuous-evals`                            | —                | Redirect → `../evaluate` (legacy URL)                                               |
| `/tasks/:id/continuous-evals/new`                        | `LiveEvalsNew`   | Wizard to create a new continuous (live) evaluation job.                            |
| `/tasks/:id/continuous-evals/:evalId`                    | `LiveEvalDetail` | Detail view for a live evaluation: status, metrics, annotation stats.               |

### Prompts & Playgrounds

| Path                                               | Component               | Description                                                                                  |
| -------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------------------- |
| `/tasks/:id/prompts`                               | `PromptsView`           | List all prompt templates associated with the task.                                          |
| `/tasks/:id/prompts-management`                    | `PromptsManagement`     | Full prompt management interface: create, edit, and version prompt templates.                |
| `/tasks/:id/prompts/:promptName`                   | `PromptsManagement`     | View/edit a specific named prompt template.                                                  |
| `/tasks/:id/prompts/:promptName/versions/:version` | `PromptsManagement`     | View a specific version of a named prompt template.                                          |
| `/tasks/:id/playgrounds/prompts`                   | `PromptsPlayground`     | Interactive prompt playground for testing prompts against LLMs with configurable parameters. |
| `/tasks/:id/notebooks`                             | `Notebooks`             | List and open prompt notebooks for exploratory prompt development.                           |
| `/tasks/:id/prompt-experiments`                    | `PromptExperimentsView` | List prompt experiments that compare prompt variants across a dataset.                       |
| `/tasks/:id/prompt-experiments/:experimentId`      | `ExperimentDetailView`  | Detail view for a single prompt experiment: per-row results and aggregate metrics.           |

### RAG

| Path                                       | Component                 | Description                                                                 |
| ------------------------------------------ | ------------------------- | --------------------------------------------------------------------------- |
| `/tasks/:id/rag`                           | `RagView`                 | RAG retrieval playground: query a configured retriever and inspect results. |
| `/tasks/:id/rag-experiments`               | `RagExperimentsListView`  | List RAG experiments that benchmark retrieval configurations.               |
| `/tasks/:id/rag-experiments/:experimentId` | `RagExperimentDetailView` | Detail view for a single RAG experiment: per-query results and scoring.     |
| `/tasks/:id/rag-notebooks`                 | `RagNotebooks`            | List RAG notebooks for iterative retrieval exploration.                     |
| `/tasks/:id/rag-notebooks/:notebookId`     | `RagExperimentsPage`      | Open a specific RAG notebook/experiment session.                            |

### Traces

| Path                | Component    | Description                                                                                                                                                         |
| ------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/tasks/:id/traces` | `TracesView` | View and filter incoming LLM traces (spans/inferences) for the task. Supports session and user-level grouping, time range filtering, and adding traces to datasets. |
