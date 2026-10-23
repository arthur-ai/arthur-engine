# UP-3208: Provider-managed validation guardrail judge

## Summary
Move the hallucination and sensitive-data validation guardrails to the shared LLM client and stored Model Providers. Add one deployment-wide judge provider/model selector in a separate Guardrail Settings tab. Remove the requirement to configure a judge LLM before engine startup or local-only validation. Preserve working provider invocation, including private certificates, TLS controls, proxy endpoints, and Azure deployment aliases.

- Status: **Requester conditionally approved proceeding after the four review comments are addressed. This revision records those changes.**
- Work item: [UP-3208](https://arthurai.atlassian.net/browse/UP-3208).
- Requester and approver: Zach Fry, GitHub `fryz`.
- Origin: [request](https://arthur-ai.slack.com/archives/C0CBALBTW78/p1792692720360599).
- Base: `dev` at `6efb897719db381e53ff6a2d672ab5ecb7ab3525`.
- This PR contains a spec only. The requester asked to merge the spec and start implementation after the comments are addressed. Keep the spec merge as a human action; do not claim that it has merged. Implementation belongs on a separate branch and draft PR under that conditional approval, not in this documentation PR.
- The Foreman must record the conditional approval and verify that the comments are addressed. GitHub approval and merge gates remain mandatory. This agent must not merge.
- Paths below are relative to `genai-engine/` unless a repository-root prefix is explicit.

## Recorded decisions
The requester reviewed the first draft and authorized proceeding once the requested changes are addressed. Preserve the unchallenged scope and apply these revisions:

1. **Global scope:** one ORG_ADMIN-owned default serves both validation LLM guardrails for every organization. No task, rule, or organization overrides.
2. **Automatic compatibility:** use the stored default when its provider is enabled. Fall back to existing environment configuration only when no default exists or the selected provider is disabled/unconfigured. Do not offer an execution-mode selector, a disable-guardrails mode, or a legacy status in the UI/API. Do not import environment secrets automatically.
3. **New credit consumption:** validation judge calls consume the owning organization's token credits and enforce its quota. This includes automatic environment fallback. This changes existing validation billing; retain it from the reviewed scope.
4. **Whitelist independence:** the service judge is independent of both the persisted provider picker whitelist and `GENAI_ENGINE_TENANT_MODEL_WHITELIST`. An admin can therefore select a judge that tenants cannot select in their own model pickers.
5. **Working invocation and lifecycle:** provider-managed guardrails must invoke correctly with the required legacy certificate/TLS, proxy, Azure API-version, alias, and local rate-control behaviors. Environment fallback is not an escape hatch for missing provider-managed compatibility. ORG_ADMIN may delete or rotate the selected provider. Deletion disables that provider and activates automatic fallback with a needs-configuration warning.
6. **Separate settings surface:** use a top tab named **Guardrail Settings**, beside **Model Providers**, under the existing settings layout. Do not embed the judge editor above the provider table or inside the provider credentials dialog.

## Product behavior

### Configuration workflow
1. An ORG_ADMIN configures credentials through the existing Model Providers editor.
2. The admin opens **Guardrail Settings** at `/settings/guardrails`. The page uses the current settings header/container and top tabs for **Model Providers** and **Guardrail Settings**.
3. The section explains: “Applies to hallucination and sensitive-data validation checks for all organizations. Judge calls consume the calling resource's organization credits. Model-picker restrictions do not limit this service model.”
4. The admin selects an enabled provider and a model. Offer its full catalog. For Azure, also allow an exact deployment alias. For OpenAI with a stored custom endpoint, also allow an exact proxy model name. An optional catalog base model supplies capability/token metadata for these aliases; it does not replace the invocation name.
5. New installations have no stored selection. An absent selection or disabled selected provider displays the warning “A model provider and model must be configured for guardrails.” Keep a disabled provider's saved selection visible for correction, but do not offer disabled providers as new choices. Do not label the application or dialog as running in legacy mode.
6. Save sends only the judge setting. It does not resend credentials, whitelists, or unrelated application settings.
7. A successful save refetches the server value and shows a success toast. A failed save preserves the form values and shows a sanitized inline error. Do not show success optimistically.
8. Provider changes clear the unsaved model and base-model selection. Accept free-text routing names only for the Azure and custom OpenAI endpoint cases above. Do not offer a fallback/legacy/disabled mode switch or a clear-to-fallback button.
9. Explain that the full catalog can include models the provider account cannot access. Saving is not a paid connection test.
10. Show loading, load failure with retry, no enabled providers, and no available catalog models states. Disable Save while required data loads or the selection is incomplete. A catalog failure must not prevent manual alias entry for Azure/custom OpenAI endpoints.
11. ORG_AUDITOR can read the tab but cannot edit it. Callers without APP_CONFIG_READ do not fetch or render it. Preserve their existing provider-page permissions and the API Keys page layout.
12. Mark the selected provider in the table for readers allowed to see the judge configuration. Its delete dialog warns: “Guardrails need a configured model provider. Removing this provider will require configuration.” ORG_ADMIN can confirm deletion. After deletion, refresh both tabs and show the needs-configuration warning.

### Validation workflow and failures
1. Apply the configured judge to `ModelHallucinationRuleV2` and `ModelSensitiveDataRule` only.
2. Cover all five route variants in `src/routers/v2/validate_routes.py`:
   - Deprecated `POST /api/v2/validate_prompt`.
   - Deprecated `POST /api/v2/validate_response/{inference_id}`.
   - `POST /api/v2/tasks/{task_id}/validate_prompt`.
   - `POST /api/v2/tasks/{task_id}/validate_response/{inference_id}`.
   - Stateless `POST /api/v2/validate`.
3. Keep each route's authentication and permission requirements. Reject missing or foreign tasks/inferences before reading judge credentials or spending tokens. Task ownership and inference ownership must both pass on task-response validation.
4. Each evaluation captures one judge configuration, credential set, model, capability decision, and billed organization. Parallel rules and nested hallucination batches use that snapshot.
5. A later save or credential rotation affects requests that capture their snapshot after that transaction commits, in every worker process. An already-started request may finish with its old snapshot.
6. Startup and local-only validation do not construct `OpenAISettings`, initialize a legacy LLM executor, resolve provider credentials, or contact a judge provider. Normal database, authentication, local-model, and rule-limit settings still apply.
7. If no default exists or its provider has no credential row, resolve the existing environment configuration lazily. In this codebase, provider `enabled=false` means that its credential row is absent. If neither source is usable, return `RuleResultEnum.UNAVAILABLE` for an otherwise executable LLM rule. Never return PASS because configuration is absent.
8. Preserve input short-circuits before judge resolution: missing hallucination context and existing rule token-limit violations remain SKIPPED. Missing local classifier weights retain MODEL_NOT_AVAILABLE semantics. A hallucination response containing no evaluable claims needs no judge call.
9. Once a rule needs a judge, absence of both usable sources yields “Guardrail judge is not configured.” Malformed stored selection, unreadable/decryption-failed credentials, invalid transport configuration, or a configuration DB failure yields “Guardrail judge configuration is unavailable.” Those errors do not trigger fallback. Do not include endpoints, credentials, or provider error bodies.
10. Convert quota exhaustion and upstream auth, rate-limit, connectivity, content-filter, context-window, parsing, and server failures to rule-level UNAVAILABLE, not a new top-level validation HTTP error. Use the existing quota message for credit exhaustion and existing safe error constants for known categories. Other failures use the existing generic evaluation error.
11. Keep independent local-rule results when an LLM rule is unavailable. Authentication, quota, upstream rate-limit, timeout, model, and parsing failures never trigger another provider or environment connection. Automatic fallback is a configuration-resolution decision, not runtime error recovery.
12. Preserve hallucination claim filtering, ordering, explanations, batch aggregation, and PARTIALLY_UNAVAILABLE when a well-formed result has the wrong label count. Invalid structured JSON remains UNAVAILABLE. Preserve sensitive-data hint/example interpretation and yes/no classification.
13. Keep validation request and response schemas, persistence, stateless non-persistence, and trace linkage unchanged. `ResponseValidationRequest.model_name` remains the model under evaluation. Do not replace it with the judge model.

### Credit attribution
1. Task prompt/response validation bills the authorized task's actual `org_id`, including when a cross-org administrator invokes it.
2. Deprecated response validation first authorizes and loads the inference. If it has a task, bill that task's organization. If it is taskless, bill `DEFAULT_ORG_ID`; tenant callers cannot authorize a taskless inference through the existing task join. Do not let a caller change task attribution by choosing the deprecated URL.
3. Stateless tenant validation bills authenticated `org_scope`. No task or inference is required.
4. Deprecated taskless prompt validation and admin stateless validation bill `utils.constants.DEFAULT_ORG_ID`. Admin taskless response validation uses the same default. `DatabaseInference` has no persisted `org_id`; do not add one. Existing taskless rule-result persistence uses `SYSTEM_ORG_ID` for historical backfill. Leave that persistence convention unchanged; it is not the new billing source.
5. Require an existing organization row. A missing organization is an internal resolution failure; return an unavailable LLM result and make no provider call. Never pass `None`, a zero UUID, or a fabricated organization to the client.
6. Check quota before each physical judge call, including explanation calls and legacy fallback calls. Record reported usage once per physical call, even if the output later fails parsing.
7. Retain the shared client's current accounting semantics: default/system organizations have no token limit, successful usage writes use independent sessions, and parallel requests can overshoot a limit because there is no token reservation. This project does not add reservations or transactional billing.
8. Local checks, skipped rules, and configuration failures do not consume LLM credits. A provider response without usage does not create an estimated charge.

## Technical design

### Current architecture
- `src/server.py:270` calls `get_scorer_client()` during lifespan startup.
- `src/dependencies.py:162` constructs singleton LLM guardrail scorers alongside heavy local scorers and metric scorers.
- `src/scorer/checks/hallucination/v2.py:126` binds an env model in its constructor. Its capability checks can independently select another random legacy connection.
- `src/scorer/checks/sensitive_data/custom_examples.py:44` binds an env model and later mutates `dynamic_prompt.examples` on that shared instance.
- `src/rules_engine.py:52` resolves the env judge's context limit in every RuleEngine constructor, including local-only requests.
- `src/scorer/llm_client.py:377` requires `OpenAISettings` and returns a global LangChain executor. It implements TLS, random connection selection, a process-local rate limiter, tokens, and invocation audit.
- `src/clients/llm/llm_client.py:241` implements provider-managed completion, quota enforcement, usage accounting, typed structured-output parsing, and HTTPException translation.
- `src/repositories/model_provider_repository.py:279` constructs a client from encrypted deployment-global credentials. `list_catalog_models_for_provider` returns the unfiltered catalog. The two picker whitelists are not enforcement in `LLMClient.completion`.
- `src/routers/v2/system_management_routes.py:106` and `:125` expose existing application-config reads/writes. APP_CONFIG_WRITE is narrower than MODEL_PROVIDER_WRITE.
- `src/db_models/configuration_models.py:7` stores unique name/string-value rows without organization columns.
- `src/monitoring/ai_activity.py:67` accumulates request invocation metadata across context-propagating worker threads.
- `src/repositories/inference_repository.py:94` scopes inference reads through task ownership; `:397` and `:439` document taskless rule-result organization stamping.
- Update validation orchestration in `src/routers/v2/validate_routes.py`, `src/validation/prompt.py`, and `src/validation/response.py`; thread the captured context through `src/rules_engine.py`, `src/scorer/score.py`, and the two guardrail scorers.

### Typed persistent setting and API
- Add one `ApplicationConfigurations.GUARDRAIL_LLM` key with value `guardrail_llm`.
- Store one serialized Pydantic model as the value of this row: `GuardrailLLMConfiguration` with `provider: ModelProvider`, `model: str`, and `base_model: str | None = None`.
- `model` is the exact provider routing identifier. `base_model` is optional metadata for Azure/custom OpenAI endpoint aliases. It is not a connection or fallback choice. Do not expose a `mode` field.
- Reject unknown fields and empty model strings. Do not store secrets, org IDs, token counts, or connection endpoints in this row.
- Extend `ApplicationConfigurationUpdateRequest`, `ApplicationConfiguration`, and `ApplicationConfigurationResponse` with `guardrail_llm`.
- Update the existing `POST /api/v2/configuration`; do not add a second write endpoint. Omitted `guardrail_llm` leaves the row unchanged. Explicit JSON null clears the row for API lifecycle/reset compatibility. The UI does not offer an execution-source choice or a clear action.
- An absent row reads as `guardrail_llm=null`. Other application-configuration writes must not materialize or overwrite it.
- Expose only `guardrail_llm_status="configured"`, `"needs_configuration"`, or `"invalid"`. A valid selection with an existing credential row is configured. An absent selection or missing provider row needs configuration. A malformed stored judge value reads as null/invalid without breaking unrelated application-config reads or local validation.
- Preserve a well-formed saved selection in the response when its provider row is missing. Reconfiguring that provider reactivates the selection automatically. Status does not guarantee remote access. Do not initialize an LLM, inspect env fallback readiness, or expose the execution source merely to serve GET configuration.
- Preserve APP_CONFIG_READ and APP_CONFIG_WRITE checks. The UI must not use MODEL_PROVIDER_WRITE as permission to edit the global default.
- No table/column migration is required. Use an atomic single-key upsert. Concurrent complete selections use last-committed-write-wins; readers must never combine half of one provider/model pair with another.

### Selection validation and provider lifecycle
- Implement configuration orchestration in new `src/services/guardrails/llm_configuration_service.py`.
- Require configured provider credentials and reject the `empty` provider placeholder.
- Validate catalog selections against `ModelProviderRepository.list_catalog_models_for_provider`, not `list_models_for_provider`. Also accept nonempty Azure deployment aliases and custom OpenAI endpoint model names outside the catalog. Reject unknown catalog-only selections for other providers and OpenAI's default endpoint.
- When supplied, validate `base_model` against the selected provider's catalog. Permit it only for Azure/custom OpenAI endpoint routing names. Use it only for capabilities, tokenizer selection, and context metadata. Never replace the routing name with it.
- Preserve routing identifiers exactly, including Azure aliases not named after a base model. Supply LiteLLM's provider identity explicitly and qualify its routing prefix exactly once. Do not strip internal slashes from an alias.
- Reuse the provider/model identity conventions from `src/services/prompt/chat_completion_service.py` and `LLMEvalsRepository.run_llm_eval`. Do not use naive double prefixing.
- Use the existing LiteLLM `supports_response_schema(model=..., custom_llm_provider=...)` pattern from `src/repositories/llm_evals_repository.py:208`, using `base_model` metadata when present. Unknown capability means existing text output, not rejection. Do not require structured output for every judge.
- Read context-window metadata from the same LiteLLM cost catalog already used by `clients/llm/llm_client.py`. Prefer positive `max_input_tokens`, then positive `max_tokens`; use the configured guardrail limit when no metadata is available.
- An alias without known metadata uses the existing text-output path and configured fallback token bound. Use `tiktoken.get_encoding("cl100k_base")` for token counting if neither metadata nor routing identity resolves to a tokenizer. Alias support is part of provider-managed acceptance, not a reason to stay on env fallback.
- For hosted vLLM, use its existing credentialed `/models` catalog lookup on save and in the editor. A failed/empty lookup prevents a new save. Do not call `/models` on every validation request.
- Do not revalidate catalog membership on every invocation. A later catalog refresh must not silently disable or replace a stored model. The provider can reject a removed model at runtime; return UNAVAILABLE without fallback.
- Whitelist changes do not clear or invalidate the judge. Include helper text that picker visibility and service selection are independent.
- Permit ORG_ADMIN deletion of the selected provider. Retain the selection, mark it needs_configuration, and use automatic environment fallback for later requests until the provider is configured again. Do not add a delete-blocking 409 or a disable-guardrails setting.
- Keep inactive provider write permissions unchanged. Require ORG_ADMIN for selected-provider credential deletion or updates; TASK_ADMIN receives 403. Keep admin secret rotation behavior intact. Apply this rule even when a retained selection currently names a disabled provider.
- Serialize configuration changes, provider credential writes, and provider deletion with one PostgreSQL transaction-scoped advisory-lock key dedicated to this setting. Use the same key for every path. Use a brief shared transaction lock when capturing configuration and credentials.
- Validate remote catalogs before acquiring the lock. Recheck local provider existence and active-provider authorization inside the lock. Commit selection or provider mutation before releasing the lock.
- Capture no DB Session or ORM object in the execution context. Release read locks before token counting, scoring, or remote model calls.
- Add PostgreSQL-backed race tests. A process-only mutex or SQLite-only test does not establish cross-process lifecycle safety.

### Request execution and scorer isolation
- Add a typed execution adapter in new `src/services/guardrails/judge_executor.py`.
- Define a frozen request context containing the internally resolved source, provider/routing model/base-model metadata, an existing billed `UUID`, structured-output capability, input limit, and an execution handle without a database session. The internal source is not an application setting or public status.
- Define a typed per-call result containing text or parsed Pydantic output and `LLMTokenConsumption`. Do not parse known response schemas through untyped dictionaries.
- Resolve authenticated resource ownership before constructing this context. Before dispatching worker threads, identify candidate LLM rules after input-only exclusions, then capture configuration and credentials with a brief resolver-owned DB session. Close that session before dispatch. Do not capture a route Session in a lazy worker callback. An unavailability result is also request-local.
- Local-only requests and requests whose LLM rules all fail input-only prerequisites do not resolve a judge. No-claim classification may run after the snapshot exists; it still makes no judge call.
- Inject the context through RuleEngine/ScorerClient rather than reading mutable singleton configuration in `score()`. Make the scoring interfaces explicitly accept this optional context for LLM rules. Local scorers and metric dispatch keep their existing behavior.
- Keep heavy classifier/embedding weights shared. Keep request examples, hints, prompts, clients bound to credentials, and billed organizations out of singleton scorer fields.
- Preserve `get_scorer_client()` as startup-safe local resource construction. Guardrail constructors no longer resolve an env model or require provider credentials.
- Build each sensitive-data example prompt from request-local values. Never assign to shared `FewShotPromptTemplate.examples`.
- Pass the same context explicitly into hallucination batch/explanation workers. Continue using `TracedThreadPoolExecutor` for audit/trace context propagation.
- Replace RuleEngine's unconditional `get_llm_executor()` token-limit lookup. Retain existing configured sensitive-data and hallucination rule limits and existing comparison boundaries. A known selected hallucination model limit replaces the fallback limit as today; an unknown model uses the configured fallback.
- Count the fully rendered messages against the selected model's known input limit before invocation, in addition to the existing rule-input checks. Map an over-limit invocation to the existing token-limit unavailable result. This protects large example/prompts without silently changing existing SKIPPED thresholds.
- Keep the existing temperature of zero when the selected provider/model accepts it. For models that do not accept temperature, omit it through provider-capability handling. Do not globally enable LiteLLM parameter dropping.

### Provider-managed calls, usage, and audit
- Every provider-managed physical call goes through `ModelProviderRepository.get_model_provider_client(...).completion(..., org_id=<resolved UUID>)`.
- That client owns quota checks and token-usage writes. The new adapter must not call `record_org_token_usage` or `LLMExecutor.execute` around this path.
- Pass `ReturnClaimFlags` as the Pydantic `response_format` when structured output is supported. Read the typed `structured_output_response`. Otherwise retain existing text-label and explanation prompts and parsing semantics.
- Use a typed raw-response observer on synchronous `LLMClient.completion`, optional and defaulting to no observer, to capture usage before structured-output parsing. Invoke it after the existing accounting step and before parsing. Do not forward the observer argument to LiteLLM.
- The observer does not write usage or audit. It captures per-call usage for the adapter's result/audit path, including when parsing raises. It must not change other callers' behavior.
- Emit exactly one `ModelInvocation` from the provider-managed adapter in a finally path: selected provider/model, existing operation name, prompt/completion/total tokens, latency, success, and sanitized exception type. Parsing errors set success false while retaining observed usage.
- Sanitize logging on the shared-client error paths reachable from judge calls. Catching and sanitizing the final rule message is not sufficient if an inner client logs the raw vendor exception.
- Missing configuration and short-circuiting rules produce no physical-call invocation record. Actual failed calls retain failure records. Audit remains opt-in and best-effort.
- Preserve tokens from completed calls in an otherwise unavailable rule result, including when a later hallucination call fails. Do not bill those tokens again during rule aggregation or inference persistence.

### Transport, aliases, and local rate-control compatibility
- Fix `LLMClient._add_provider_credentials` in `src/clients/llm/llm_client.py` to pass a stored OpenAI `api_base`. The repository already stores and reconstructs it. Preserve Azure's stored endpoint and API version. Never replace DB credentials, routing names, endpoints, or API version with the env connection triple when a configured provider is selected.
- Add an optional OpenAI custom-endpoint field to the existing credential editor. Use its current encrypted `api_base` API field. Do not duplicate endpoints or secrets in `guardrail_llm`.
- Factor transport-only settings from `src/config/openai_config.py` so resolving optional `GENAI_ENGINE_OPENAI_VERIFY_SSL` and `GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL` never requires provider/model/key/rate variables. Preserve `OPENAI_CONFIG_FILE` and `.env` loading precedence.
- Apply those existing TLS controls to provider-managed OpenAI/Azure judge calls as well as environment fallback. A configured private certificate uses `ssl.create_default_context(cafile=OPENAI_PRIVATE_CERT_PATH)` and takes precedence over VERIFY_SSL=false, matching `OpenAISettings.get_ssl_verify`. With neither override, preserve normal certificate verification. An unreadable configured CA fails closed with UNAVAILABLE.
- Use a typed optional SDK-client override on the shared LLM client for guardrail calls. Construct `openai.OpenAI` or `openai.AzureOpenAI` with the snapshot's credentials/endpoint/version and an `httpx.Client(verify=<resolved policy>)`; pass the SDK client through LiteLLM's per-call `client` hook. The pinned LiteLLM 1.105.1 supports this hook for OpenAI and Azure. Do not mutate `litellm.ssl_verify`, `litellm.client_session`, or process-global SDK credentials.
- Reuse transports only under keys that include provider, endpoint, credential revision, and TLS policy. Keep transport lifetimes separate from DB sessions. Do not close an in-flight snapshot's transport during rotation. Do not apply a guardrail-only override to unrelated shared-client consumers.
- Preserve the validation process-local token-per-period limiter on both provider-managed and fallback paths. Load existing rate settings optionally, default to 20,000 tokens per 60 seconds, synchronize concurrent updates, and apply it once per physical call. Invalid explicit values make the judge unavailable. Keep organization quota checks and reported-usage accounting separate from this limiter.
- Require actual configured-provider invocation regression tests below. Mocked SDK kwargs alone do not prove correct routing, TLS handshake, aliases, or parsing.

### Automatic environment compatibility adapter
- Missing judge configuration never causes startup to initialize the legacy executor.
- Only when the default is absent or its provider is disabled, load connection settings lazily from `OPENAI_CONFIG_FILE` and its existing `.env` behavior. Missing/invalid model connections yield a sanitized unavailable result without logging the connection contract.
- Treat legacy rate settings as optional for validation: use the existing limiter defaults of 20,000 tokens per 60 seconds when values are absent. Invalid explicitly supplied values yield configuration unavailable.
- Keep the existing OpenAI/Azure connection parsing, transport/private-CA behavior, API version, and rate-control semantics. Select one connection at request resolution and pin its model for the whole evaluation. Random distribution therefore moves from long-lived scorer construction to request capture.
- Determine structured-output support and the context limit from that selected model and provider. Do not call helpers that randomly select a second model.
- The validation adapter may reuse legacy connection construction and a lazily cached transport/limiter. It must not store request sessions, orgs, examples, or prompts there. Synchronize limiter updates for concurrent validation calls.
- Check organization quota before each physical call. Write reported usage once in a finally path, including when parsing fails. The implementation uses raw `AIMessage.usage_metadata` and JSON-mode structured output with `include_raw=True`: real invocation tests exposed lost usage on malformed structured responses and Azure model-name errors in the aggregate LangChain callback. This changes only the guardrail adapter, not other legacy consumers.
- Emit one invocation audit record from this adapter. Do not additionally call `LLMExecutor.execute`, which would duplicate audit and rate accounting.
- Leave legacy executor behavior for relevance/tool metrics, chat, and embeddings unchanged. Do not remove their OpenAISettings or alter their independent billing.
- Provider-managed invocation must preserve the transport/rate behavior specified above. Only random multi-connection pooling remains specific to environment fallback; migrating a pool to multiple DB credential sets is out of scope.

### UI and generated contracts
- Add a sibling `/settings/guardrails` route in `ui/src/App.tsx` using the existing `ProtectedRoute` and `SettingsPage` boundaries. Add shared top-tab navigation for Model Providers and Guardrail Settings under `ui/src/components/settings/`. Keep `/settings/model-providers` and existing task redirects working. Do not add these tabs to API Keys.
- Add the isolated MUI editor under `ui/src/components/settings/guardrail-settings/`. Keep credential editing in `ui/src/components/model-providers/`; the judge selector must not live above its provider table.
- Follow `ui/CLAUDE.md`: MUI components, theme tokens through `sx`, generated API types, central query keys, `useApiQuery`, and `useApiMutation`.
- Reuse the full catalog returned by the existing whitelist-read API for the admin editor, not the tenant-filtered available-model endpoint. Do not change what existing user model pickers display.
- Add configuration hooks next to the provider hooks. Gate config requests by APP_CONFIG_READ roles from authenticated identity. Invalidate/refetch configuration after save, and refresh provider/catalog data after credential changes.
- Extend selected-provider delete/rotation warnings and refresh the configuration status after deletion, recreation, or rotation. The backend remains authoritative when cached state is stale. No UI copy, option, or badge describes an application legacy/fallback mode.
- Regenerate `staging.openapi.json`, the API changelog, and `ui/src/lib/api-client/api-client.ts` through the existing generators. Never hand-edit the generated client.

## Decisions and alternatives
- **One global default over per-org/task/rule settings:** global matches existing credentials, configuration storage, and the request. Scoped settings offer tenant autonomy but require new ownership and precedence design. Defer them to the broader configuration work.
- **One typed JSON row over two scalar rows or explicit modes:** one row prevents mismatched provider/model reads. A nullable default captures configuration without exposing execution-source choices. It needs typed serialization but no schema migration.
- **Automatic fallback over a mode selector or clean break:** the requester requires fallback when a provider is disabled and does not want legacy state shown. Resolve it internally only for absent/disabled configuration. A clean break disrupts env-only deployments; a user-selected legacy mode adds rejected UX. Import can overwrite secrets and cannot represent random pools losslessly.
- **Quota accounting over a service-wide free judge:** the shared client requires a real organization. Account for every validation call, including automatic fallback, to avoid an unmetered alternate path. Retain this reviewed scope. Do not change quotas or migrate unrelated consumers.
- **Full catalog over picker whitelist enforcement:** current whitelists control user picker visibility, not execution authorization. An admin service model must remain stable when tenant picker options change. The trade-off is that tenants can incur judge credits for a model they cannot pick themselves.
- **Allow deletion with a warning over blocking deletion or cascade-clear:** the requester's disabled-provider fallback requires this lifecycle to remain operable. Retain the selection so provider recreation restores it. Require ORG_ADMIN for selected-provider mutations to prevent TASK_ADMIN from redirecting the global service. The intentional trade-off is automatic env invocation after deletion, not after provider call failures.
- **Aliases plus optional base metadata over catalog-only routing:** catalog-only selection rejects working Azure/proxy deployments and fails the requester's compatibility requirement. Separate routing identity from metadata. Unknown metadata uses text output and a fallback token bound instead of inventing capabilities.
- **Per-client transport over global TLS mutation or fallback-only compatibility:** the configured global provider must work with existing private CA/proxy deployments. Isolated SDK transports add lifecycle work but prevent one request from changing another caller's security policy. Keeping such deployments only on env fallback was explicitly rejected.
- **Top tabs over an embedded provider-table section or a new sidebar:** sibling settings tabs distinguish judge policy from credentials without introducing another navigation system. Preserve the current settings shell and provider route.
- **Request snapshots over singleton mutation or process caching:** snapshots prevent cross-tenant state leaks and restart-dependent configuration. They add brief per-evaluation DB reads. Heavy local weights stay shared.
- **Rule-level failures over propagated provider HTTP status:** validation already carries per-rule availability. Preserve that contract, including credit exhaustion, and keep unaffected local results.

## Assumptions
- **Assumption A1:** The requester's “once addressed” instruction conditionally approves unchallenged first-draft choices. The Foreman records that approval; it does not substitute for GitHub's required human approval.
- **Assumption A2:** Catalog entries are not promises of account access or reliable judge output. Azure/custom OpenAI endpoint aliases are supported independently of catalog membership.
- **Assumption A3:** Optional `base_model` metadata and retaining a deleted provider's selection are implementation choices made to satisfy alias compatibility and automatic reactivation. The requester did not specify these data-shape details.
- **Assumption A4:** Legacy compatibility lasts through this release. No removal date or later migration is promised.
- **Assumption A5:** Existing non-client rule-limit environment settings remain operational settings. “No judge env required” removes the startup dependency on LLM provider/model/key/endpoint/rate settings; it does not remove unrelated deployment configuration.
- **Assumption A6:** Old binaries ignore the new configuration key. A binary rollback needs the old judge environment retained or restored. API null/reset or provider deletion activates automatic fallback in this release; neither is exposed as a legacy-mode UI control.

## Out of scope
- Per-task, per-rule, or per-org defaults, bring-your-own tenant credentials, and model overrides in validation payloads.
- Migration of relevance, tool-selection metrics, chat, embeddings, OOTB evals, or chatbot configuration.
- Removing the legacy executor/configuration while those consumers still use it.
- Automatic secret import, pooled provider credentials, runtime error-triggered credential fallback, and new private-CA configuration UI. Existing private-CA/TLS controls, Azure aliases, and OpenAI's stored proxy endpoint support are in scope.
- Judge prompt redesign, classifier retraining, result enum changes, or a general quota reservation/billing redesign.
- Expanding existing provider/tenant read access or changing existing user model-picker filtering.
- Deployment template cleanup that would remove env values still used by out-of-scope consumers.

## Operator migration and rollback
1. Read the release note before switching. Identify every remaining metric/chat/embedding consumer of legacy env settings.
2. Env-only deployments continue automatically until a default is configured. The UI warns that guardrails need configuration; it does not display legacy mode. Single and comma-separated connection triples remain supported on this internal fallback path. Pin one selected connection per evaluation.
3. Configure the destination provider through the existing encrypted credentials API/UI. Inspect existing credentials before changing them; this feature never imports or overwrites them.
4. Open Guardrail Settings and select an enabled provider and model or supported alias. Verify account access with an authorized validation request. Confirm quota, usage, output, and audit behavior.
5. For multi-connection pools, choose one supported provider/model explicitly. There is no lossless automatic import or pooling in provider-managed mode.
6. For proxies/private CAs, store the OpenAI custom endpoint or Azure endpoint/version and preserve the existing optional TLS deployment settings. Use the exact deployment/proxy alias. Provider-managed invocation must pass the transport regressions before release; remaining on env fallback does not satisfy this gate.
7. Observe successful judge validation before removing any legacy setting. Do not remove settings required by out-of-scope consumers.
8. If a provider fails after switching, fix its credentials/model/transport. Runtime failure never silently reactivates env fallback. Removing its credentials activates automatic fallback and the needs-configuration warning. Reconfiguring it restores the saved selection.
9. No new switch stops all judge calls. Removing provider credentials does not stop them when env fallback is configured. To roll back to an older binary, restore its legacy env requirements first.

## Validation criteria
These checks are implementation acceptance gates. The spec-only PR does not claim they already pass. New test names below are required targets, not existing tests.

### Backend: deterministic functional and security checks
Run from `genai-engine/`: `uv run pytest tests/ -m "unit_tests" --cov=src --cov-fail-under=79`.

- Add `tests/unit/validation/test_guardrail_judge_configuration.py`:
  - `test_startup_and_local_validation_without_judge_env`: remove judge provider/key/model/endpoint/rate variables, prevent `.env` from restoring them, stub heavy model downloads, execute actual lifespan/scorer construction and all local rule types; assert no OpenAISettings, provider client, or judge network call.
  - `test_config_precedence_and_automatic_fallback`: absent row + valid env, absent row + no env, provider selection + conflicting env, selected provider disabled + valid/no env, explicit null reset, malformed stored value, and unreadable existing credentials. Only absent selection/missing provider row permit fallback.
  - `test_no_runtime_fallback`: parameterize DB-read failure, auth failure, quota failure, rate limit, timeout, content filter, missing model, parse failure, and provider 5xx; assert no alternate env/client call.
  - `test_request_snapshot_refreshes_across_sessions`: update config/credentials in one session and assert new evaluations in separate service instances see the commit while in-flight snapshots stay stable.
  - `test_configuration_and_errors_do_not_expose_secrets`: API responses, exceptions, logs, audit, and UI-safe error details contain no credential, connection triple, private key, or private endpoint.
- Extend `tests/unit/routes/configuration/test_configurations.py`:
  - `test_guardrail_config_atomic_save_and_omission`: round-trip provider/model/base_model, null clears, absent fields preserve values and unrelated settings, invalid/incomplete selections do not commit, and mode fields are rejected. Assert only configured/needs_configuration/invalid statuses and no public execution-source field.
  - `test_guardrail_config_permissions`: ORG_ADMIN writes, ORG_AUDITOR reads only, TASK_ADMIN/TENANT_USER/unauthenticated callers cannot alter the setting; no credential fields in responses.
- Extend `tests/unit/repositories/test_model_provider_repository.py` and `tests/unit/routes/model_providers_and_secrets/test_model_provider_and_secrets_endpoints.py`:
  - `test_guardrail_catalog_and_alias_selection`: reject disabled provider, empty sentinel, unknown catalog-only model, invalid base_model, and failed vLLM catalog; accept catalog entries outside both picker whitelists plus Azure/custom OpenAI endpoint aliases absent from the catalog. Preserve routing names exactly.
  - `test_guardrail_provider_lifecycle`: ORG_ADMIN selected-provider deletion succeeds and preserves selection; later requests fall back and GET reports needs_configuration; recreation reactivates the selection; TASK_ADMIN selected deletion/rotation/recreation returns 403; ORG_ADMIN rotation works; unrelated provider operations retain permissions; whitelist changes preserve judge selection.
  - `test_no_credential_import_or_overwrite`: selection changes leave encrypted credentials byte-for-byte unchanged.
- Add `tests/unit/validation/test_guardrail_judge_routes.py`:
  - `test_guardrail_route_matrix`: exercise the five route variants above with each executable LLM guardrail, configured provider and automatic env fallback; assert selected provider/model, result shape, token fields, trace/persistence behavior, and unchanged model-under-evaluation.
  - `test_guardrail_org_attribution`: tenant task, cross-org admin task, tenant stateless, admin stateless, default taskless prompt, deprecated response with task, and taskless persisted inference.
  - `test_unauthorized_validation_spends_no_tokens`: foreign/missing task or inference returns existing 404/403/401 semantics; assert no judge call and no quota/usage mutation.
  - `test_quota_and_usage_exactly_once`: assert each physical call checks quota; sum provider usage once per org across batches/explanations and parse failures; no writes on skipped/local/config failures; no-credit UNAVAILABLE retains local results.
- Extend `tests/unit/test_hallucination.py`, `tests/unit/test_sensitive_data.py`, `tests/unit/scorer/test_llm_client.py`, and `tests/unit/clients/llm/test_llm_client.py`:
  - `test_selected_model_capabilities_limits_and_audit`: distinguish structured/non-structured models, known/unknown context sizes, multi-triple random selections, and an env model different from the stored model. Invocation, limits, capabilities, and audit must use the same captured identity.
  - `test_structured_legacy_and_partial_output_contract`: preserve claim filtering/order/reasons, no-claim behavior, incorrect label count, malformed JSON, sensitive yes/no behavior, and aggregated usage.
  - `test_sensitive_examples_are_request_local`: use barriers to interleave two orgs, rule hints, and example sets; assert rendered prompts, results, usage, and audit do not cross requests.
  - `test_judge_audit_once_in_nested_workers`: successful calls, upstream failures, parsing errors, opt-in off, and a second request after cleanup; verify exact invocation counts and tokens without duplicate legacy-executor records.
  - `test_raw_observer_does_not_change_other_completion_callers`: ensure the observer is optional, never sent to LiteLLM, and cannot duplicate usage.
- Extend existing `tests/unit/routes/test_builtin_validate.py`, `tests/unit/routes/tasks/test_task_validate_prompt.py`, and `tests/unit/validation/` coverage for response-contract regressions.

### Compatibility and cross-process checks
- In `tests/unit/validation/test_guardrail_judge_configuration.py`, add `test_transport_settings_and_rate_defaults` for both resolved sources: private CA precedence over VERIFY_SSL=false, default verification, unreadable CA fails closed, OPENAI_CONFIG_FILE precedence, limiter defaults/invalid explicit settings, and single/multiple env triples. Assert no required GPT env dependency in the configured-provider path and no global LiteLLM transport mutation.
- Add `tests/integration/test_guardrail_judge_provider_invocation.py`, marked `integration_tests`. Run a local OpenAI/Azure-compatible HTTP(S) test server with an ephemeral test CA/certificate. Use the real configuration repository, provider factory, LLMClient, LiteLLM SDK transport, and guardrail adapters; do not mock completion, the SDK client, or TLS verification. No external vendor credentials or paid calls are required.
  - `test_configured_openai_judge_invokes_without_judge_env`: configure encrypted provider credentials and global selection, remove GPT/provider/key/model/rate env inputs, and execute both guardrails against the server. Assert outbound model, expected non-UNAVAILABLE result, actual usage attribution, and one invocation record per physical call.
  - `test_configured_proxy_alias_and_base_path_are_preserved`: configure a custom `/proxy/v1/` endpoint and a model alias absent from the catalog. Assert the exact outbound path/model/auth header and working text output; repeat with a base_model enabling structured output. Conflicting valid env connection details must receive zero calls.
  - `test_configured_azure_deployment_alias_and_api_version_are_preserved`: configure an alias absent from the catalog, Azure endpoint, and stored API version. Assert the exact deployment path/API-version query and working text/structured judge results. Base-model metadata must not replace the deployment alias.
  - `test_configured_provider_private_ca_tls_and_verification`: parameterize OpenAI proxy and Azure. Require success with the configured private CA, handshake failure with default trust, and success with explicit VERIFY_SSL=false only when no private CA is configured. Assert missing/invalid CA remains UNAVAILABLE and no env fallback call occurs.
  - `test_configured_transport_isolation_and_rotation`: interleave two independently configured transports and rotate credentials. Assert no credential/CA crossover, no mutation of unrelated clients, stable in-flight snapshots, and refreshed later requests.
- Run the actual-invocation suite with `uv run pytest tests/integration/test_guardrail_judge_provider_invocation.py -m integration_tests`. These configured-global-provider checks are release gates, not optional legacy-path coverage.
- Add `tests/integration/test_guardrail_judge_configuration_locking.py`, marked `integration_tests`, using two independent PostgreSQL connections/processes:
  - `test_default_save_vs_provider_delete_is_serialized`.
  - `test_active_rotation_permission_rechecked_under_lock`.
  - `test_snapshot_reads_consistent_config_and_credentials`.
- Run those tests against the documented local PostgreSQL setup: `uv run pytest tests/integration/test_guardrail_judge_configuration_locking.py -m integration_tests`.
- Run existing regression targets with `uv run pytest -m unit_tests tests/unit/scorer/test_relevance_scorer.py tests/unit/scorer/test_tool_selection.py tests/unit/test_chat.py tests/unit/test_embedding.py`. Confirm they keep legacy configuration. Do not rewrite those consumers to make the new tests pass.

### API, quality, UI, and visual proof
- Run `uv run routes_security_check`.
- Run `uv run --group linters mypy src`, `uv run black --check src tests`, and `uv run isort --check-only src tests --profile black`; distinguish pre-existing failures from new failures.
- Run `PYTHONPATH=src uv run generate_changelog`. The generator can exit 1 when it updates files; rerun after reviewing generated changes and require no further change.
- Regenerate the UI client from the resulting `staging.openapi.json` with `yarn generate-api:clean` from `genai-engine/ui/`. Repeating code generation must leave no uncommitted diff.
- Add `ui/src/components/settings/guardrail-settings/index.test.tsx` and hook tests covering sibling tabs/routes, roles, full catalog vs picker whitelist, alias/base-model entry, incomplete form, loading/empty/error/retry, failed-save retention, successful save/refetch, needs-configuration warnings, selected-provider deletion/recreation, and refresh after rotation. Assert no legacy/fallback/disable-mode selector or legacy status copy is rendered.
- Run `yarn check`, `yarn test:run`, and `yarn build` from `genai-engine/ui/`.
- After the build succeeds, use the computer-use tool on a running app. Capture a video navigating the sibling settings tabs, admin configuration/save, reload persistence, LLM validation using the configured global provider, failed save, selected-provider deletion with warning, needs-configuration state, and successful provider recreation. Show automatic fallback using a test env connection and UNAVAILABLE when neither source exists. Demonstrate read-only/non-admin behavior with test identities.
- Attach that video and screenshots of the saved/default and error/permission states to the implementation PR description. Browser proof cannot be replaced by component-test output.
- The requester has made the spec PR non-draft and conditionally authorized the spec and implementation once the four comments are addressed. Do not redraft or merge it automatically. Obtain the required current-head human approval and satisfy merge gates for the spec. Implementation must use a separate branch and new draft PR targeting dev, cite this revised spec, and include the required visual proof and review. Starting that separate work does not mean the spec has merged or waive either PR's gates.

## Related work
- [UP-3107](https://arthurai.atlassian.net/browse/UP-3107): original shared-eval foundation.
- [UP-3381](https://arthurai.atlassian.net/browse/UP-3381): historical backend default-model/env-import proposal; not authorization to import secrets.
- [XP-757](https://arthurai.atlassian.net/browse/XP-757): broader task/rule/chat configuration; deferred here.
