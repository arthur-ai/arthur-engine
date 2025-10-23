import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { SyntheticEvent, useEffect, useMemo } from "react";

import { usePromptContext } from "./PromptsPlaygroundContext";
import { PromptType } from "./types";

import useSnackbar from "@/hooks/useSnackbar";
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
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const { state, dispatch } = usePromptContext();

  const handleSelectPrompt = (
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

    // dispatch({
    //   type: "updatePrompt",
    //   payload: { promptId: prompt.id, prompt: backendPromptData },
    // });
  };

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
  const backendPromptOptions = state.backendPrompts.map(
    (backendPrompt) => backendPrompt.name
  );
  const availableModels = useMemo(
    () => state.availableModels.get(prompt.provider as ModelProvider) || [],
    [state.availableModels, prompt.provider]
  );

  return (
    <>
      <div className="w-1/3">
        <Autocomplete
          id={`prompt-select-${prompt.id}`}
          options={backendPromptOptions}
          value={currentPromptName}
          onChange={handleSelectPrompt}
          disabled={state.backendPrompts.length === 0}
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
      </div>
      <div className="w-1/3">
        <Tooltip
          title={
            providerDisabled
              ? "No providers available. Please configure at least one provider."
              : ""
          }
          placement="top-start"
          arrow
        >
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
