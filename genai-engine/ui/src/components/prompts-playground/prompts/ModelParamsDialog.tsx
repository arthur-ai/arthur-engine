import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";
import { v4 as uuidv4 } from "uuid";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { ModelParametersType } from "../types";

import { AnthropicThinkingParamInputTypeEnum, LogitBiasItem } from "@/lib/api-client/api-client";
import { track } from "@/services/analytics";

const EFFORT_OPTIONS = ["none", "minimal", "low", "medium", "high", "default"];

const THINKING_TYPE_OPTIONS: AnthropicThinkingParamInputTypeEnum[] = ["enabled", "adaptive"];

// A single editable logit_bias row. Values are kept as strings so the inputs can be
// cleared freely; they are parsed into numbers on submit. `id` is a stable React key.
interface LogitBiasDraft {
  id: string;
  token_id: string;
  bias: string;
}

const toLogitBiasDrafts = (items: LogitBiasItem[] | null | undefined): LogitBiasDraft[] =>
  items && items.length > 0 ? items.map((item) => ({ id: uuidv4(), token_id: String(item.token_id), bias: String(item.bias) })) : [];

const draftsToLogitBias = (drafts: LogitBiasDraft[]): LogitBiasItem[] =>
  drafts
    .filter((draft) => draft.token_id.trim() !== "" && draft.bias.trim() !== "")
    .map((draft) => ({ token_id: Number(draft.token_id), bias: Number(draft.bias) }));

const ModelParamsForm = ({
  promptId,
  name,
  modelParameters,
  onClose,
}: {
  promptId: string;
  name: string;
  modelParameters: ModelParametersType;
  onClose: () => void;
}) => {
  const { dispatch } = usePromptContext();
  const [copiedParams, setCopiedParams] = useState<ModelParametersType>(modelParameters);
  const [logitBiasRows, setLogitBiasRows] = useState<LogitBiasDraft[]>(() => toLogitBiasDrafts(modelParameters.logit_bias));

  const handleAddLogitBias = () => {
    setLogitBiasRows((prev) => [...prev, { id: uuidv4(), token_id: "", bias: "" }]);
  };

  const handleRemoveLogitBias = (index: number) => {
    setLogitBiasRows((prev) => prev.filter((_, i) => i !== index));
  };

  const handleLogitBiasChange = (index: number, field: "token_id" | "bias", value: string) => {
    setLogitBiasRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const formJson = Object.fromEntries(formData.entries()) as Record<string, string>;

    // Convert empty strings to null for numeric and optional fields
    const processedParams: Partial<ModelParametersType> = {};

    // Numeric fields that should be null when empty
    const numericFields = [
      "temperature",
      "top_p",
      "timeout",
      "max_tokens",
      "max_completion_tokens",
      "frequency_penalty",
      "presence_penalty",
      "seed",
    ] as const;
    numericFields.forEach((field) => {
      const value = formJson[field];
      processedParams[field] = value === "" || value === undefined ? null : Number(value);
    });

    // Optional text fields
    const textFields = ["stop"] as const;
    textFields.forEach((field) => {
      const value = formJson[field];
      processedParams[field] = value === "" || value === undefined ? null : value;
    });

    // Boolean field (stream) - checkbox is only included when checked
    // If not in formJson, the checkbox was unchecked, so set to false
    processedParams.stream = formJson.stream === "on";

    // Select field (reasoning_effort)
    const reasoningEffortValue = formJson.reasoning_effort;
    processedParams.reasoning_effort =
      reasoningEffortValue === "" || reasoningEffortValue === undefined ? null : (reasoningEffortValue as ModelParametersType["reasoning_effort"]);

    // Advanced fields (logprobs, top_logprobs, stream_options, thinking) are controlled
    // via copiedParams. Logit bias rows are the only advanced editing buffer, assembled here.
    const logitBiasItems = draftsToLogitBias(logitBiasRows);
    const updatedParams: ModelParametersType = {
      ...copiedParams,
      ...processedParams,
      logit_bias: logitBiasItems.length > 0 ? logitBiasItems : null,
    };

    onClose();

    dispatch({
      type: "updateModelParameters",
      payload: { promptId, modelParameters: updatedParams },
    });

    // Track model parameters changed event
    const paramCount = Object.keys(processedParams).filter(
      (key) => processedParams[key as keyof ModelParametersType] !== null && processedParams[key as keyof ModelParametersType] !== undefined
    ).length;
    track("Model Params Changed", {
      model_provider: name ? name.split(":")[0] : undefined,
      model_name: name ? name.split(":")[1] : undefined,
      param_count: paramCount,
    });
  };

  return (
    <>
      <DialogTitle>Model Parameters{name ? `: ${name}` : ""}</DialogTitle>
      <DialogContent>
        <DialogContentText>Tune the model parameters for your prompt.</DialogContentText>
        <br />
        <form onSubmit={handleSubmit} id="model-params-form" className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="temperature" className="w-3/5">
              Temperature
            </InputLabel>
            <TextField
              key="temperature"
              id="temperature"
              name="temperature"
              defaultValue={modelParameters.temperature ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: 0,
                  max: 2,
                  step: 0.1,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="top_p" className="w-3/5">
              Top P
            </InputLabel>
            <TextField
              key="top_p"
              id="top_p"
              name="top_p"
              defaultValue={modelParameters.top_p ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: 0,
                  max: 1,
                  step: 0.1,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="timeout" className="w-3/5">
              Timeout
            </InputLabel>
            <TextField
              key="timeout"
              id="timeout"
              name="timeout"
              defaultValue={modelParameters.timeout ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: 0,
                  step: 1,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="stream" className="w-3/5">
              Stream
            </InputLabel>
            <Checkbox
              key="stream"
              id="stream"
              name="stream"
              checked={copiedParams.stream ?? false}
              onChange={(event) => {
                setCopiedParams({ ...copiedParams, stream: event.target.checked });
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="max_tokens" className="w-3/5">
              Max Tokens
            </InputLabel>
            <TextField
              key="max_tokens"
              id="max_tokens"
              name="max_tokens"
              defaultValue={modelParameters.max_tokens ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: 0,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="max_completion_tokens" className="w-3/5">
              Max Completion Tokens
            </InputLabel>
            <TextField
              key="max_completion_tokens"
              id="max_completion_tokens"
              name="max_completion_tokens"
              defaultValue={modelParameters.max_completion_tokens ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: 0,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="frequency_penalty" className="w-3/5">
              Frequency Penalty
            </InputLabel>
            <TextField
              key="frequency_penalty"
              id="frequency_penalty"
              name="frequency_penalty"
              defaultValue={modelParameters.frequency_penalty ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: -2,
                  max: 2,
                  step: 0.1,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="presence_penalty" className="w-3/5">
              Presence Penalty
            </InputLabel>
            <TextField
              key="presence_penalty"
              id="presence_penalty"
              name="presence_penalty"
              defaultValue={modelParameters.presence_penalty ?? ""}
              size="small"
              className="w-2/5"
              type="number"
              slotProps={{
                htmlInput: {
                  min: -2,
                  max: 2,
                  step: 0.1,
                },
              }}
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="stop" className="w-3/5">
              Stop
            </InputLabel>
            <TextField key="stop" id="stop" name="stop" defaultValue={modelParameters.stop ?? ""} size="small" className="w-2/5" type="text" />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="seed" className="w-3/5">
              Seed
            </InputLabel>
            <TextField key="seed" id="seed" name="seed" defaultValue={modelParameters.seed ?? ""} size="small" className="w-2/5" type="number" />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="reasoning_effort" className="w-3/5">
              Reasoning Effort
            </InputLabel>
            <Select
              key="reasoning_effort"
              id="reasoning_effort"
              name="reasoning_effort"
              defaultValue={modelParameters.reasoning_effort ?? ""}
              size="small"
              className="w-2/5"
              type="text"
            >
              {(Object.values(EFFORT_OPTIONS) as string[]).map((effort) => (
                <MenuItem key={effort} value={effort}>
                  {effort}
                </MenuItem>
              ))}
            </Select>
          </div>
          <Accordion
            disableGutters
            elevation={0}
            sx={{
              mt: 1,
              border: 1,
              borderColor: "divider",
              borderRadius: 1,
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2">Advanced</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={1}>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <InputLabel htmlFor="logprobs" className="w-3/5">
                    Log Probabilities
                  </InputLabel>
                  <Checkbox
                    id="logprobs"
                    checked={copiedParams.logprobs ?? false}
                    onChange={(event) => {
                      setCopiedParams({ ...copiedParams, logprobs: event.target.checked });
                    }}
                  />
                </Stack>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <InputLabel htmlFor="top_logprobs" className="w-3/5">
                    Top Log Probabilities
                  </InputLabel>
                  <TextField
                    id="top_logprobs"
                    value={copiedParams.top_logprobs ?? ""}
                    onChange={(event) => {
                      const value = event.target.value;
                      setCopiedParams((prev) => ({ ...prev, top_logprobs: value === "" ? null : Number(value) }));
                    }}
                    size="small"
                    className="w-2/5"
                    type="number"
                    slotProps={{
                      htmlInput: {
                        min: 0,
                        max: 20,
                        step: 1,
                      },
                    }}
                  />
                </Stack>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <InputLabel htmlFor="include_usage" className="w-3/5">
                    Stream Usage
                  </InputLabel>
                  <Checkbox
                    id="include_usage"
                    checked={copiedParams.stream_options?.include_usage ?? false}
                    onChange={(event) => {
                      setCopiedParams({
                        ...copiedParams,
                        stream_options: event.target.checked ? { include_usage: true } : null,
                      });
                    }}
                  />
                </Stack>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <InputLabel htmlFor="thinking_type" className="w-3/5">
                    Thinking
                  </InputLabel>
                  <Select
                    id="thinking_type"
                    value={copiedParams.thinking?.type ?? ""}
                    onChange={(event) => {
                      const type = event.target.value as "" | AnthropicThinkingParamInputTypeEnum;
                      setCopiedParams((prev) => ({
                        ...prev,
                        thinking: type === "" ? null : { type, budget_tokens: prev.thinking?.budget_tokens },
                      }));
                    }}
                    size="small"
                    className="w-2/5"
                    displayEmpty
                  >
                    <MenuItem value="">
                      <em>none</em>
                    </MenuItem>
                    {THINKING_TYPE_OPTIONS.map((type) => (
                      <MenuItem key={type} value={type}>
                        {type}
                      </MenuItem>
                    ))}
                  </Select>
                </Stack>
                <Stack direction="row" alignItems="center" spacing={1}>
                  <InputLabel htmlFor="budget_tokens" className="w-3/5">
                    Thinking Budget Tokens
                  </InputLabel>
                  <TextField
                    id="budget_tokens"
                    value={copiedParams.thinking?.budget_tokens ?? ""}
                    onChange={(event) => {
                      const value = event.target.value;
                      const budget = value === "" ? undefined : Number(value);
                      setCopiedParams((prev) =>
                        prev.thinking?.type ? { ...prev, thinking: { type: prev.thinking.type, budget_tokens: budget } } : prev
                      );
                    }}
                    disabled={!copiedParams.thinking?.type}
                    size="small"
                    className="w-2/5"
                    type="number"
                    slotProps={{
                      htmlInput: {
                        min: 0,
                        step: 1,
                      },
                    }}
                  />
                </Stack>
                <Stack spacing={0.75}>
                  <InputLabel>Logit Bias</InputLabel>
                  {logitBiasRows.map((row, index) => (
                    <Box key={row.id} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <TextField
                        label="Token ID"
                        value={row.token_id}
                        onChange={(event) => handleLogitBiasChange(index, "token_id", event.target.value)}
                        size="small"
                        type="number"
                        fullWidth
                      />
                      <TextField
                        label="Bias"
                        value={row.bias}
                        onChange={(event) => handleLogitBiasChange(index, "bias", event.target.value)}
                        size="small"
                        type="number"
                        fullWidth
                        slotProps={{
                          htmlInput: {
                            min: -100,
                            max: 100,
                          },
                        }}
                      />
                      <IconButton aria-label="remove logit bias" size="small" onClick={() => handleRemoveLogitBias(index)}>
                        <DeleteIcon fontSize="small" color="error" />
                      </IconButton>
                    </Box>
                  ))}
                  <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
                    <Button variant="text" size="small" startIcon={<AddIcon />} onClick={handleAddLogitBias}>
                      Add logit bias
                    </Button>
                  </Box>
                </Stack>
              </Stack>
            </AccordionDetails>
          </Accordion>
        </form>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button type="submit" form="model-params-form">
          Save
        </Button>
      </DialogActions>
    </>
  );
};

const ModelParamsDialog = ({
  open,
  setOpen,
  promptId,
  name,
  modelParameters,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
  promptId: string;
  name: string;
  modelParameters: ModelParametersType;
}) => {
  const handleClose = () => {
    setOpen(false);
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth>
      {open && <ModelParamsForm promptId={promptId} name={name} modelParameters={modelParameters} onClose={handleClose} />}
    </Dialog>
  );
};

export default ModelParamsDialog;
