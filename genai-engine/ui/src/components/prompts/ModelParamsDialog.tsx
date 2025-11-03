import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import React, { useState } from "react";

import { usePromptContext } from "./PromptsPlaygroundContext";
import { ModelParametersType } from "./types";

const EFFORT_OPTIONS = ["none", "minimal", "low", "medium", "high", "default"];

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
  const { dispatch } = usePromptContext();
  const [copiedParams, setCopiedParams] = useState<ModelParametersType>(modelParameters);

  const handleClose = () => {
    setOpen(false);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const formJson = Object.fromEntries(formData.entries()) as Record<string, string>;
    setCopiedParams((state) => ({ ...state, ...formJson }));
    handleClose();

    dispatch({
      type: "updateModelParameters",
      payload: { promptId, modelParameters: copiedParams },
    });
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth>
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
              defaultValue={modelParameters.temperature}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
              defaultValue={modelParameters.top_p}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
              defaultValue={modelParameters.timeout}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
              defaultChecked={modelParameters.stream} // Only appears in form when true
            />
          </div>
          {/* <div className="flex items-center gap-2">
            <InputLabel htmlFor="stream_options" className="w-3/5">
              Stream Options
            </InputLabel>
          </div> */}
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="max_tokens" className="w-3/5">
              Max Tokens
            </InputLabel>
            <TextField
              key="max_tokens"
              id="max_tokens"
              name="max_tokens"
              defaultValue={modelParameters.max_tokens}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
              defaultValue={modelParameters.max_completion_tokens}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
              defaultValue={modelParameters.frequency_penalty}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
              defaultValue={modelParameters.presence_penalty}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
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
            <TextField
              key="stop"
              id="stop"
              name="stop"
              defaultValue={modelParameters.stop}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
              type="text"
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="seed" className="w-3/5">
              Seed
            </InputLabel>
            <TextField
              key="seed"
              id="seed"
              name="seed"
              defaultValue={modelParameters.seed}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
              type="number"
            />
          </div>
          <div className="flex items-center gap-2">
            <InputLabel htmlFor="reasoning_effort" className="w-3/5">
              Reasoning Effort
            </InputLabel>
            <Select
              key="reasoning_effort"
              id="reasoning_effort"
              name="reasoning_effort"
              defaultValue={modelParameters.reasoning_effort}
              size="small"
              className="w-2/5 border-gray-300 border-2 rounded-md"
              type="text"
            >
              {(Object.values(EFFORT_OPTIONS) as string[]).map((effort) => (
                <MenuItem key={effort} value={effort}>
                  {effort}
                </MenuItem>
              ))}
            </Select>
          </div>
        </form>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button type="submit" form="model-params-form">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ModelParamsDialog;
