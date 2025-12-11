import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { SyntheticEvent, useEffect, useEffectEvent, useRef, useState } from "react";

import { useBackendPrompts } from "../hooks/useBackendPrompts";
import { useBackendPromptVersion } from "../hooks/useBackendPromptVersion";
import { useAvailableModels, useProviders } from "../hooks/useProviders";
import { usePromptPlaygroundStore } from "../stores/playground.store";
import { PromptType } from "../types";
import toFrontendPrompt from "../utils/toFrontendPrompt";

import VersionSelector from "./VersionSelector";

import useSnackbar from "@/hooks/useSnackbar";
import { ModelProvider, LLMGetAllMetadataResponse, AgenticPrompt } from "@/lib/api-client/api-client";

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
  const { snackbarProps, alertProps } = useSnackbar();

  const [selectedPromptVersion, setSelectedPromptVersion] = useState<number | null>(null);

  const actions = usePromptPlaygroundStore((state) => state.actions);

  const promptVersion = useBackendPromptVersion(currentPromptName, selectedPromptVersion?.toString() ?? "");
  const providers = useProviders();
  const availableModels = useAvailableModels(prompt.modelProvider || undefined);
  const backendPrompts = useBackendPrompts();

  const enabledProviders = providers.data?.filter((provider) => provider.enabled).map((provider) => provider.provider) ?? [];

  const onPromptVersionChange = useEffectEvent((promptVersion: AgenticPrompt) => {
    const parsed = toFrontendPrompt(promptVersion);

    actions.setPrompt(prompt.id, parsed);
  });

  useEffect(() => {
    if (!promptVersion.data) return;

    onPromptVersionChange(promptVersion.data);
  }, [promptVersion.data]);

  const handleSelectPrompt = (_event: SyntheticEvent<Element, Event>, newValue: LLMGetAllMetadataResponse | null) => {
    const selection = newValue?.name || "";

    if (selection === "") {
      return;
    }

    onPromptNameChange(selection);
  };

  const handleVersionSelect = async (version: number) => {
    setSelectedPromptVersion(version);
  };

  const handleProviderChange = (_event: SyntheticEvent<Element, Event>, newValue: ModelProvider | null) => {
    actions.setPromptProvider(prompt.id, newValue);
  };

  const handleModelChange = (_event: SyntheticEvent<Element, Event>, newValue: string | null) => {
    actions.setPromptModelName(prompt.id, newValue);
  };

  const handleLoad = useEffectEvent(() => {
    if (enabledProviders?.length && !prompt.modelProvider && !prompt.version) {
      actions.setPromptProvider(prompt.id, enabledProviders[0]);
    }
  });

  useEffect(() => {
    handleLoad();
  }, []);

  const providerDisabled = enabledProviders.length === 0;
  const modelDisabled = prompt.modelProvider === "";
  const tooltipTitle = providerDisabled ? "No providers available. Please configure at least one provider." : "";
  const backendPromptOptions = backendPrompts.data?.llm_metadata.map((backendPrompt) => backendPrompt.name) ?? [];

  return (
    <div className="flex gap-1 min-w-0 flex-wrap">
      <div className="flex-1 min-w-0">
        <Autocomplete
          id={`prompt-select-${prompt.id}`}
          options={backendPrompts.data?.llm_metadata ?? []}
          value={backendPrompts.data?.llm_metadata.find((bp) => bp.name === currentPromptName) || null}
          onChange={handleSelectPrompt}
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
      <VersionSelector
        promptName={currentPromptName}
        promptId={prompt.id}
        currentVersion={prompt.version}
        isDirty={prompt.isDirty}
        onVersionSelect={handleVersionSelect}
      />
      <div className="flex-1 min-w-0">
        <Tooltip title={tooltipTitle} placement="top-start" arrow>
          <Autocomplete<ModelProvider>
            id={`provider-${prompt.id}`}
            options={enabledProviders}
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
          options={availableModels.data ?? []}
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
