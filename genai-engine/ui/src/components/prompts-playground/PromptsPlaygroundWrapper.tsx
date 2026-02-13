import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { parseAsString, useQueryStates } from "nuqs";
import { useMemo } from "react";

import { useDeserializedNotebookState } from "./hooks/useDeserializedNotebookState";
import PromptsPlayground from "./PromptsPlayground";
import { PlaygroundInitialData, PromptType } from "./types";
import apiToFrontendPrompt from "./utils/apiToFrontendPrompt";
import { serializePlaygroundState } from "./utils/notebookStateUtils";
import toFrontendPrompt from "./utils/toFrontendPrompt";

import { usePrompt } from "@/components/prompts-management/hooks/usePrompt";
import { useNotebook } from "@/hooks/useNotebooks";
import { usePromptExperiment, usePromptExperiments } from "@/hooks/usePromptExperiments";
import { useSpan } from "@/hooks/useSpan";
import { useTask } from "@/hooks/useTask";
import type { PromptExperimentDetail, PromptExperimentSummary } from "@/lib/api-client/api-client";

export const playgroundParams = {
  notebookId: parseAsString,
  spanId: parseAsString,
  experimentId: parseAsString,
  promptName: parseAsString,
  promptVersion: parseAsString,
  version: parseAsString,
};

/**
 * Resolves all async data before mounting the inner playground.
 * Eliminates hydration useEffects from the inner component.
 */
const PromptsPlaygroundWrapper = () => {
  const [params] = useQueryStates(playgroundParams);
  const { notebookId, spanId, experimentId, promptName, version: promptVersionParam } = params;
  const promptVersion = params.promptVersion;

  const { task } = useTask();

  const isConfigMode = !!(experimentId && promptName && promptVersion);

  const { notebook, isLoading: notebookLoading } = useNotebook(notebookId ?? undefined);
  const {
    prompts: nbPrompts,
    keywords: nbKeywords,
    fullState: nbFullState,
    isLoading: nbStateLoading,
  } = useDeserializedNotebookState(notebookId ?? undefined, task?.id);

  const { span: spanData, isLoading: spanLoading } = useSpan(spanId ?? undefined);

  const { experiment: experimentData, isLoading: experimentLoading } = usePromptExperiment(isConfigMode ? (experimentId ?? undefined) : undefined);
  const { prompt: experimentPromptData, isLoading: experimentPromptLoading } = usePrompt(
    task?.id,
    isConfigMode ? (promptName ?? undefined) : undefined,
    isConfigMode ? (promptVersion ?? undefined) : undefined
  );
  const { experiments: allExperiments, isLoading: experimentsListLoading } = usePromptExperiments(isConfigMode ? task?.id : undefined);

  const { prompt: urlPromptData, isLoading: urlPromptLoading } = usePrompt(
    task?.id,
    !isConfigMode ? (promptName ?? undefined) : undefined,
    !isConfigMode ? (promptVersionParam ?? undefined) : undefined
  );

  const isLoading = useMemo(() => {
    if (notebookId && (notebookLoading || nbStateLoading)) return true;
    if (spanId && spanLoading) return true;
    if (isConfigMode && (experimentLoading || experimentPromptLoading || experimentsListLoading)) return true;
    if (!isConfigMode && promptName && promptVersionParam && urlPromptLoading) return true;
    return false;
  }, [
    notebookId,
    notebookLoading,
    nbStateLoading,
    spanId,
    spanLoading,
    isConfigMode,
    experimentLoading,
    experimentPromptLoading,
    experimentsListLoading,
    promptName,
    promptVersionParam,
    urlPromptLoading,
  ]);

  const initialData: PlaygroundInitialData = useMemo(() => {
    let prompts: PromptType[] = [];
    let keywords = new Map<string, string>();
    let experimentConfig: Partial<PromptExperimentDetail> | null = null;
    let experimentRuns: PromptExperimentSummary[] = [];
    let configModeActive = isConfigMode;
    let sourceType: PlaygroundInitialData["source"]["type"] = "blank";
    let sourceLabel = "";

    if (isConfigMode && experimentData && experimentPromptData) {
      const frontendPrompt = toFrontendPrompt(experimentPromptData);
      prompts = [frontendPrompt];
      experimentConfig = experimentData;
      configModeActive = true;

      if (allExperiments) {
        experimentRuns = allExperiments.filter((exp: PromptExperimentSummary) => exp.name === experimentData.name);
      }

      if (experimentData.prompt_variable_mapping && experimentData.prompt_variable_mapping.length > 0) {
        experimentData.prompt_variable_mapping.forEach((mapping) => {
          keywords.set(mapping.variable_name, "");
        });
      }

      sourceType = "experiment";
      sourceLabel = `Opened experiment for ${promptName}`;
    }
    else if (notebookId && nbPrompts && nbKeywords) {
      const hasPromptUrlParams = promptName && promptVersionParam;
      const notebookIsEmpty = nbPrompts.length === 0;

      if (hasPromptUrlParams && notebookIsEmpty && urlPromptData) {
        const frontendPrompt = toFrontendPrompt(urlPromptData);
        prompts = [frontendPrompt];
        keywords = new Map();
        sourceType = "url-prompt";
        sourceLabel = frontendPrompt.name
          ? `Opened playground for ${frontendPrompt.name}${frontendPrompt.version ? ` v${frontendPrompt.version}` : ""}`
          : "Playground loaded";
      } else {
        prompts = nbPrompts;
        keywords = nbKeywords;
        sourceType = "notebook";
        if (nbPrompts.length > 0) {
          const first = nbPrompts[0];
          sourceLabel = first.name ? `Opened playground for ${first.name}${first.version ? ` v${first.version}` : ""}` : "Playground loaded";
        } else {
          sourceLabel = "Playground loaded";
        }
      }

      if (nbFullState?.dataset_ref) {
        experimentConfig = {
          name: notebook?.name || "Notebook Experiment",
          description: notebook?.description || "",
          dataset_ref: nbFullState.dataset_ref,
          eval_list: nbFullState.eval_list || [],
          prompt_variable_mapping: nbFullState.prompt_variable_mapping || [],
          dataset_row_filter: nbFullState.dataset_row_filter || [],
        };
        configModeActive = true;
      }
    }
    else if (spanData) {
      const spanPrompt = apiToFrontendPrompt(spanData);
      prompts = [spanPrompt];
      sourceType = "span";
      sourceLabel = `Opened playground for ${spanPrompt.name || "span"}`;
    }
    else if (!isConfigMode && urlPromptData) {
      const frontendPrompt = toFrontendPrompt(urlPromptData);
      prompts = [frontendPrompt];
      sourceType = "url-prompt";
      sourceLabel = frontendPrompt.name
        ? `Opened playground for ${frontendPrompt.name}${frontendPrompt.version ? ` v${frontendPrompt.version}` : ""}`
        : "Playground loaded";
    }

    const syntheticState = {
      keywords,
      keywordTracker: new Map<string, Array<string>>(),
      prompts,
      backendPrompts: [],
    };
    const autoSaveBaseline = JSON.stringify(serializePlaygroundState(syntheticState, experimentConfig));

    return {
      prompts,
      keywords,
      notebookName: notebook?.name || "",
      experimentConfig,
      experimentRuns,
      isConfigMode: configModeActive,
      autoSaveBaseline,
      source: { type: sourceType, label: sourceLabel },
    };
  }, [
    isConfigMode,
    experimentData,
    experimentPromptData,
    allExperiments,
    promptName,
    promptVersionParam,
    notebookId,
    nbPrompts,
    nbKeywords,
    nbFullState,
    urlPromptData,
    spanData,
    notebook,
  ]);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  const dataSourceKey = `${notebookId ?? ""}-${spanId ?? ""}-${experimentId ?? ""}-${promptName ?? ""}-${promptVersionParam ?? ""}-${promptVersion ?? ""}`;

  return <PromptsPlayground key={dataSourceKey} initialData={initialData} />;
};

export default PromptsPlaygroundWrapper;
