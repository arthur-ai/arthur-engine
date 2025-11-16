import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { SyntheticEvent, useEffect, useMemo, useRef, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptType } from "../types";
import toFrontendPrompt from "../utils/toFrontendPrompt";

import VersionSelector from "./VersionSelector";

import { useApi } from "@/hooks/useApi";
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";
import { ModelProvider, LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";

const PROVIDER_TEXT = "Select Provider";
const PROMPT_NAME_TEXT = "Select Prompt";
const MODEL_TEXT = "Select Model";

const TruncatedText = ({ text }: { text: string }) => {
  const textRef = useRef<HTMLDivElement>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  useEffect(() => {
    const checkTruncation = () => {
      if (textRef.current) {
        const isTextTruncated = textRef.current.scrollWidth > textRef.current.clientWidth;
        setIsTruncated(isTextTruncated);
      }
    };

    checkTruncation();
    // Recheck on window resize
    window.addEventListener("resize", checkTruncation);
    return () => window.removeEventListener("resize", checkTruncation);
  }, [text]);

  const content = (
    <Typography
      variant="body1"
      color="text.primary"
      sx={{
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}
      ref={textRef}
    >
      {text}
    </Typography>
  );

  if (isTruncated) {
    return (
      <Tooltip title={text} placement="top">
        {content}
      </Tooltip>
    );
  }

  return content;
};

const PromptSelectors = ({
  prompt,
  currentPromptName,
  onPromptNameChange,
}: {
  prompt: PromptType;
  currentPromptName: string;
  onPromptNameChange: (name: string) => void;
}) => {
  const apiClient = useApi();
  const { task } = useTask();
  const { state, dispatch } = usePromptContext();
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const fetchAndLoadPromptVersion = async (promptName: string, version: number) => {
    if (!apiClient || !task?.id) {
      throw new Error("API client not available");
    }

    try {
      // Fetch the specific version's full data
      const response = await apiClient.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
        promptName,
        version.toString(),
        task?.id
      );
      // Convert to frontend format and update prompt
      const frontendPrompt = toFrontendPrompt(response.data);
      dispatch({
        type: "updatePrompt",
        payload: { promptId: prompt.id, prompt: frontendPrompt },
      });
    } catch (error) {
      console.error("Failed to fetch prompt version:", error);
      showSnackbar("Failed to load prompt version", "error");
      throw error;
    }
  };

  const handleSelectPrompt = async (_event: SyntheticEvent<Element, Event>, newValue: LLMGetAllMetadataResponse | null) => {
    const selection = newValue?.name || "";
    if (selection === "") {
      return;
    }
    onPromptNameChange(selection);

    const backendPromptData = state.backendPrompts.find((bp) => bp.name === selection);

    if (typeof backendPromptData === "undefined") {
      showSnackbar("Prompt not found", "error");
      return;
    }

    if (!apiClient || !task?.id) {
      showSnackbar("API client or task not available", "error");
      return;
    }

    try {
      // Fetch the latest version of the prompt
      await fetchAndLoadPromptVersion(selection, backendPromptData.versions);
    } catch (error) {
      console.error("Error handling prompt selection:", error);
      showSnackbar("Failed to load prompt", "error");
      onPromptNameChange(""); // Reset on error
    }
  };

  const handleVersionSelect = async (version: number) => {
    try {
      await fetchAndLoadPromptVersion(currentPromptName, version);
    } catch (error) {
      console.error("Failed to load selected version:", error);
      showSnackbar("Failed to load prompt version", "error");
    }
  };

  const handleProviderChange = (_event: SyntheticEvent<Element, Event>, newValue: ModelProvider | null) => {
    dispatch({
      type: "updatePromptProvider",
      payload: { promptId: prompt.id, modelProvider: newValue || "" },
    });
  };

  const handleModelChange = (_event: SyntheticEvent<Element, Event>, newValue: string | null) => {
    dispatch({
      type: "updatePromptModelName",
      payload: { promptId: prompt.id, modelName: newValue || "" },
    });
  };

  // Set the first provider as the default provider (only for new prompts without a provider)
  // Skip this if the prompt already has a provider set (when loading from backend)
  useEffect(() => {
    // Only set default provider for truly new prompts (no provider and no version)
    if (state.enabledProviders.length > 0 && !prompt.modelProvider && !prompt.version) {
      dispatch({
        type: "updatePromptProvider",
        payload: {
          promptId: prompt.id,
          modelProvider: state.enabledProviders[0],
        },
      });
    }
  }, [state.enabledProviders, dispatch, prompt.id, prompt.modelProvider, prompt.version]);

  const providerDisabled = state.enabledProviders.length === 0;
  const modelDisabled = prompt.modelProvider === "";
  const tooltipTitle = providerDisabled ? "No providers available. Please configure at least one provider." : "";
  const backendPromptOptions = state.backendPrompts.map((backendPrompt) => backendPrompt.name);
  const availableModels = useMemo(
    () => state.availableModels.get(prompt.modelProvider as ModelProvider) || [],
    [state.availableModels, prompt.modelProvider]
  );

  return (
    <div className="flex gap-1 min-w-0 flex-wrap">
      <div className="flex-1 min-w-0">
        <Autocomplete
          id={`prompt-select-${prompt.id}`}
          options={state.backendPrompts}
          value={state.backendPrompts.find((bp) => bp.name === currentPromptName) || null}
          onChange={(_event, newValue) => handleSelectPrompt(_event, newValue)}
          getOptionLabel={(option) => option.name}
          isOptionEqualToValue={(option, value) => option.name === value?.name}
          disabled={backendPromptOptions.length === 0}
          noOptionsText="No saved prompts"
          renderOption={(props, option) => {
            const { key, ...optionProps } = props;
            return (
              <Box key={key} component="li" sx={{ "& > img": { mr: 2, flexShrink: 0 } }} {...optionProps}>
                <Box
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                    minWidth: 0,
                  }}
                >
                  <TruncatedText text={option.name} />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ ml: 1, flexShrink: 0 }}>
                  ({option.versions})
                </Typography>
              </Box>
            );
          }}
          renderInput={(params) => (
            <TextField {...params} label={PROMPT_NAME_TEXT} variant="outlined" size="small" sx={{ backgroundColor: "white" }} />
          )}
        />
      </div>
      <VersionSelector promptName={currentPromptName} promptId={prompt.id} currentVersion={prompt.version} isDirty={prompt.isDirty} onVersionSelect={handleVersionSelect} />
      <div className="flex-1 min-w-0">
        <Tooltip title={tooltipTitle} placement="top-start" arrow>
          <Autocomplete<ModelProvider>
            id={`provider-${prompt.id}`}
            options={state.enabledProviders}
            value={prompt.modelProvider || null}
            onChange={handleProviderChange}
            disabled={providerDisabled}
            renderInput={(params) => (
              <TextField {...params} label={PROVIDER_TEXT} variant="outlined" size="small" sx={{ backgroundColor: "white" }} />
            )}
          />
        </Tooltip>
      </div>
      <div className="flex-1 min-w-0">
        <Autocomplete
          id={`model-${prompt.id}`}
          options={availableModels}
          value={prompt.modelName || ""}
          onChange={handleModelChange}
          disabled={modelDisabled}
          renderInput={(params) => <TextField {...params} label={MODEL_TEXT} variant="outlined" size="small" sx={{ backgroundColor: "white" }} />}
        />
      </div>
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </div>
  );
};

export default PromptSelectors;
