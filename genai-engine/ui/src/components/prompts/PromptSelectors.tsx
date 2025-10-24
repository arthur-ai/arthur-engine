import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { SyntheticEvent, useEffect, useMemo, useRef, useState } from "react";

import { usePromptContext } from "./PromptsPlaygroundContext";
import { PromptType } from "./types";
import { toFrontendPrompt } from "./utils";
import VersionSubmenu from "./VersionSubmenu";

import { useApi } from "@/hooks/useApi";
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";
import { ModelProvider } from "@/lib/api-client/api-client";

const PROVIDER_TEXT = "Select Provider";
const PROMPT_NAME_TEXT = "Select Prompt";
const MODEL_TEXT = "Select Model";

const PromptSelectors = ({
  prompt,
  currentPromptName,
  onPromptNameChange,
}: {
  prompt: PromptType;
  currentPromptName: string;
  onPromptNameChange: (name: string) => void;
}) => {
  const promptSelectorRef = useRef<HTMLDivElement>(null);
  const [versionSubmenuOpen, setVersionSubmenuOpen] = useState(false);
  const [selectedPromptForVersions, setSelectedPromptForVersions] = useState<
    string | null
  >(null);
  const apiClient = useApi();
  const { task } = useTask();
  const { state, dispatch } = usePromptContext();
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const handleSelectPrompt = async (
    _event: SyntheticEvent<Element, Event>,
    newValue: string | null
  ) => {
    const selection = newValue || "";
    if (selection === "") {
      return;
    }
    onPromptNameChange(selection);

    const backendPromptData = state.backendPrompts.find(
      (bp) => bp.name === selection
    );

    if (typeof backendPromptData === "undefined") {
      showSnackbar("Prompt not found", "error");
      return;
    }

    if (!apiClient || !task?.id) {
      showSnackbar("API client or task not available", "error");
      return;
    }

    try {
      if (backendPromptData.versions === 1) {
        // Single version - fetch directly
        await fetchAndLoadPromptVersion(selection, task.id, 1);
        setVersionSubmenuOpen(false);
      } else {
        // Multiple versions - open modal
        setSelectedPromptForVersions(selection);
        setVersionSubmenuOpen(true);
      }
    } catch (error) {
      console.error("Error handling prompt selection:", error);
      showSnackbar("Failed to load prompt", "error");
      onPromptNameChange(""); // Reset on error
    }
  };

  const fetchAndLoadPromptVersion = async (
    promptName: string,
    taskId: string,
    version: number
  ) => {
    if (!apiClient) {
      throw new Error("API client not available");
    }

    try {
      // Fetch the specific version's full data
      const response =
        await apiClient.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
          promptName,
          version.toString(),
          taskId
        );

      // Convert to frontend format and update prompt
      const frontendPrompt = toFrontendPrompt(response.data);
      dispatch({
        type: "updatePrompt",
        payload: { promptId: prompt.id, prompt: frontendPrompt },
      });
    } catch (error) {
      console.error("Failed to fetch prompt version:", error);
      throw error;
    }
  };

  const handleVersionSelect = async (version: number) => {
    if (!selectedPromptForVersions || !task?.id) {
      console.log("asdf2");
      showSnackbar("Prompt or task not available", "error");
      return;
    }

    try {
      await fetchAndLoadPromptVersion(
        selectedPromptForVersions,
        task.id,
        version
      );
      setVersionSubmenuOpen(false);
      setSelectedPromptForVersions(null);
    } catch (error) {
      console.error("Failed to load selected version:", error);
      showSnackbar("Failed to load prompt version", "error");
    }
  };

  const handleSubmenuClose = () => {
    setVersionSubmenuOpen(false);
    setSelectedPromptForVersions(null);
    onPromptNameChange(""); // Reset prompt selector
  };

  // Close submenu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        promptSelectorRef.current &&
        !promptSelectorRef.current.contains(event.target as Node)
      ) {
        setVersionSubmenuOpen(false);
      }
    };

    if (versionSubmenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [versionSubmenuOpen]);

  const handleProviderChange = (
    _event: SyntheticEvent<Element, Event>,
    newValue: string | null
  ) => {
    dispatch({
      type: "updatePromptProvider",
      payload: { promptId: prompt.id, provider: newValue || "" },
    });
  };

  const handleModelChange = (
    _event: SyntheticEvent<Element, Event>,
    newValue: string | null
  ) => {
    dispatch({
      type: "updatePromptModelName",
      payload: { promptId: prompt.id, modelName: newValue || "" },
    });
  };

  // Set the first provider as the default provider
  useEffect(() => {
    if (state.enabledProviders.length > 0) {
      dispatch({
        type: "updatePromptProvider",
        payload: { promptId: prompt.id, provider: state.enabledProviders[0] },
      });
    }
  }, [state.enabledProviders, dispatch, prompt.id]);

  const providerDisabled = state.enabledProviders.length === 0;
  const modelDisabled = prompt.provider === "";
  const tooltipTitle = providerDisabled
    ? "No providers available. Please configure at least one provider."
    : "";
  const backendPromptOptions = state.backendPrompts.map(
    (backendPrompt) => backendPrompt.name
  );
  const availableModels = useMemo(
    () => state.availableModels.get(prompt.provider as ModelProvider) || [],
    [state.availableModels, prompt.provider]
  );

  return (
    <>
      <div
        className="w-1/3"
        ref={promptSelectorRef}
        style={{ position: "relative" }}
      >
        <Autocomplete
          id={`prompt-select-${prompt.id}`}
          options={backendPromptOptions}
          value={currentPromptName}
          onChange={handleSelectPrompt}
          disabled={backendPromptOptions.length === 0}
          renderInput={(params) => (
            <TextField
              {...params}
              label={PROMPT_NAME_TEXT}
              variant="standard"
              sx={{
                backgroundColor: "white",
              }}
            />
          )}
        />
        <VersionSubmenu
          promptName={selectedPromptForVersions || ""}
          taskId={task?.id || ""}
          apiClient={apiClient!}
          onVersionSelect={handleVersionSelect}
          onClose={handleSubmenuClose}
          open={versionSubmenuOpen}
          anchorEl={promptSelectorRef.current}
        />
      </div>
      <div className="w-1/3">
        <Tooltip title={tooltipTitle} placement="top-start" arrow>
          <Autocomplete
            id={`provider-${prompt.id}`}
            options={state.enabledProviders}
            value={prompt.provider || ""}
            onChange={handleProviderChange}
            disabled={providerDisabled}
            renderInput={(params) => (
              <TextField
                {...params}
                label={PROVIDER_TEXT}
                variant="standard"
                sx={{
                  backgroundColor: "white",
                }}
              />
            )}
          />
        </Tooltip>
      </div>
      <div className="w-1/3">
        <Autocomplete
          id={`model-${prompt.id}`}
          options={availableModels}
          value={prompt.modelName || ""}
          onChange={handleModelChange}
          disabled={modelDisabled}
          renderInput={(params) => (
            <TextField
              {...params}
              label={MODEL_TEXT}
              variant="standard"
              sx={{
                backgroundColor: "white",
              }}
            />
          )}
        />
      </div>
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};

export default PromptSelectors;
