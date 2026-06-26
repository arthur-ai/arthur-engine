import { useRegisterPreparation } from "@arthur/shared-components/tour";
import type { PreparationHook } from "@arthur/shared-components/tour";
import { useCallback, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { TASK_TOUR_PREPARATIONS } from "../content/wiring";
import { DEMO_TASK_PROMPT_NAME } from "../widgets/PromptTargetWidget";

import { useApi } from "@/hooks/useApi";
import { buildFetchDatasetsParams } from "@/services/datasetService";

/**
 * Preparation hooks that establish a step's DYNAMIC detail route when it's
 * entered out of order (checklist jump / resume). These steps omit a static
 * `route` because their URL depends on a runtime id/name (`/evaluators/:name`,
 * `/datasets/:id`, `/prompts/:name`, or the playground's
 * `/playgrounds/prompts?promptName=…&version=latest`) and normally rely on a
 * prior step's click to navigate there — which never happens on a jump.
 *
 * Each hook is a no-op when the user is already on a matching detail route (so
 * the linear flow and sequential sub-steps don't re-navigate); otherwise it
 * resolves the demo entity (the same "first / demo" entity the linear tour
 * highlights) and navigates. Resolution failure returns `{ ready: false }`, so
 * the engine falls back to the target-lost hint rather than hanging.
 *
 * Mirrors {@link import("./useTracesTourPrep").useTracesTourPrep}: registered
 * from `TaskTourPortal` (inside `<TourProvider>`), reads app state through
 * hooks, and closes over stable refs so the registered callbacks don't churn.
 */
export interface UseDetailRouteTourPrepOptions {
  taskId: string;
}

export function useDetailRouteTourPrep({ taskId }: UseDetailRouteTourPrepOptions): void {
  const api = useApi();
  const navigate = useNavigate();
  const location = useLocation();

  const apiRef = useRef(api);
  apiRef.current = api;
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const pathnameRef = useRef(location.pathname);
  pathnameRef.current = location.pathname;
  const taskIdRef = useRef(taskId);
  taskIdRef.current = taskId;

  // Evaluator detail — /tasks/:taskId/evaluators/:evalName
  const evaluatorHook = useCallback<PreparationHook>(async () => {
    if (/\/evaluators\/[^/]+/.test(pathnameRef.current)) return { ready: true };
    const tid = taskIdRef.current;
    let evalName: string | null = null;
    try {
      const response = await apiRef.current?.api.getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet({ taskId: tid, page: 0, page_size: 1 });
      evalName = response?.data.llm_metadata?.[0]?.name ?? null;
    } catch {
      // fall through to the not-ready hint
    }
    if (!evalName) return { ready: false };
    navigateRef.current(`/tasks/${tid}/evaluators/${encodeURIComponent(evalName)}`);
    return { ready: true };
  }, []);

  // Dataset detail — /tasks/:taskId/datasets/:datasetId
  const datasetHook = useCallback<PreparationHook>(async () => {
    if (/\/datasets\/[^/]+/.test(pathnameRef.current)) return { ready: true };
    const tid = taskIdRef.current;
    let datasetId: string | null = null;
    try {
      const params = buildFetchDatasetsParams(tid, { sortOrder: "desc", page: 0, pageSize: 1 });
      const response = await apiRef.current?.api.getDatasetsApiV2TasksTaskIdDatasetsSearchGet(params);
      datasetId = response?.data.datasets?.[0]?.id ?? null;
    } catch {
      // fall through to the not-ready hint
    }
    if (!datasetId) return { ready: false };
    navigateRef.current(`/tasks/${tid}/datasets/${datasetId}`);
    return { ready: true };
  }, []);

  // Prompt detail — /tasks/:taskId/prompts/:promptName (demo prompt name is known)
  const promptHook = useCallback<PreparationHook>(async () => {
    if (/\/prompts\/[^/]+/.test(pathnameRef.current)) return { ready: true };
    const tid = taskIdRef.current;
    navigateRef.current(`/tasks/${tid}/prompts/${encodeURIComponent(DEMO_TASK_PROMPT_NAME)}`);
    return { ready: true };
  }, []);

  // Prompt playground — /tasks/:taskId/playgrounds/prompts?promptName=…&version=latest
  // Uses the playground's "url-prompt" data source (no notebook required). The
  // backend resolves `version=latest` to the latest non-deleted version (same
  // as the prompt detail page), so no version lookup is needed here.
  const playgroundHook = useCallback<PreparationHook>(() => {
    if (/\/playgrounds\/prompts/.test(pathnameRef.current)) return { ready: true };
    const tid = taskIdRef.current;
    navigateRef.current(`/tasks/${tid}/playgrounds/prompts?promptName=${encodeURIComponent(DEMO_TASK_PROMPT_NAME)}&version=latest`);
    return { ready: true };
  }, []);

  // Experiment detail — /tasks/:taskId/prompt-experiments/:experimentId
  const experimentHook = useCallback<PreparationHook>(async () => {
    if (/\/prompt-experiments\/[^/]+/.test(pathnameRef.current)) return { ready: true };
    const tid = taskIdRef.current;
    let experimentId: string | null = null;
    try {
      const response = await apiRef.current?.api.listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet({ taskId: tid, page: 0, page_size: 1 });
      experimentId = response?.data.data?.[0]?.id ?? null;
    } catch {
      // fall through to the not-ready hint
    }
    if (!experimentId) return { ready: false };
    navigateRef.current(`/tasks/${tid}/prompt-experiments/${experimentId}`);
    return { ready: true };
  }, []);

  useRegisterPreparation(TASK_TOUR_PREPARATIONS.evaluatorDetailOpened, evaluatorHook);
  useRegisterPreparation(TASK_TOUR_PREPARATIONS.datasetDetailOpened, datasetHook);
  useRegisterPreparation(TASK_TOUR_PREPARATIONS.promptDetailOpened, promptHook);
  useRegisterPreparation(TASK_TOUR_PREPARATIONS.playgroundOpened, playgroundHook);
  useRegisterPreparation(TASK_TOUR_PREPARATIONS.experimentDetailOpened, experimentHook);
}
