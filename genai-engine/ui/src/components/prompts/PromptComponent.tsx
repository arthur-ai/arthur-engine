import React, { useCallback, useState } from "react";
import { PromptComponentProps } from "./types";
import MessageComponent from "./MessageComponent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import { providerEnum } from "./types";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Tooltip from "@mui/material/Tooltip";
import Container from "@mui/material/Container";
import Paper from "@mui/material/Paper";
import AddIcon from "@mui/icons-material/Add";

const PROVIDER_TEXT = "Provider";
const PROMPT_NAME_TEXT = "Prompt Name";
const MODEL_TEXT = "Model";

// TODO: Pull from backend
const PROMPT_NAME_OPTIONS = [
  { label: "Prompt 1", value: "prompt1" },
  { label: "Prompt 2", value: "prompt2" },
  { label: "Prompt 3", value: "prompt3" },
];

const MODEL_OPTIONS = [
  { label: "Model 1", value: "model1" },
  { label: "Model 2", value: "model2" },
  { label: "Model 3", value: "model3" },
];

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt, dispatch }: PromptComponentProps) => {
  const [provider, setProvider] = useState<string>(providerEnum.OPENAI);

  const handleProviderChange = (event: SelectChangeEvent) => {
    setProvider(event.target.value);
  };

  const handleDeletePrompt = useCallback(() => {
    dispatch({
      type: "deletePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleDuplicatePrompt = useCallback(() => {
    dispatch({
      type: "duplicatePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleAddMessage = useCallback(() => {
    dispatch({
      type: "addMessage",
      payload: { parentId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  return (
    <div className="bg-purple-500 min-h-[500px]">
      <Container component="div" className="p-1" maxWidth="xl" disableGutters>
        <div className="grid grid-cols-2 gap-1">
          <div className="flex justify-start items-center gap-1">
            <div className="w-1/3">
              <FormControl fullWidth size="small" variant="filled">
                <InputLabel id="prompt-name">{PROMPT_NAME_TEXT}</InputLabel>
                <Select
                  labelId="prompt-name"
                  id="prompt-name"
                  label={PROMPT_NAME_TEXT}
                  value={null}
                  onChange={() => {}}
                >
                  {PROMPT_NAME_OPTIONS.map((promptNameOption) => (
                    <MenuItem
                      key={promptNameOption.value}
                      value={promptNameOption.value}
                    >
                      {promptNameOption.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth size="small" variant="filled">
                <InputLabel id="provider">{PROVIDER_TEXT}</InputLabel>
                <Select
                  labelId="provider"
                  id="provider"
                  label={PROVIDER_TEXT}
                  value={provider}
                  onChange={handleProviderChange}
                >
                  {Object.values(providerEnum).map((providerValue) => (
                    <MenuItem key={providerValue} value={providerValue}>
                      {providerValue}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth size="small" variant="filled">
                <InputLabel id="model">{MODEL_TEXT}</InputLabel>
                <Select
                  labelId="model"
                  id="model"
                  label={MODEL_TEXT}
                  value={null}
                  onChange={() => {}}
                >
                  {MODEL_OPTIONS.map((modelOption) => (
                    <MenuItem key={modelOption.value} value={modelOption.value}>
                      {modelOption.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
          </div>
          <div className="flex justify-end items-center gap-1">
            <Tooltip title="Add Message" placement="top" arrow>
              <IconButton aria-label="add" onClick={handleAddMessage}>
                <AddIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Duplicate Prompt" placement="top" arrow>
              <IconButton
                aria-label="duplicate"
                onClick={handleDuplicatePrompt}
              >
                <ContentCopyIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Save Prompt" placement="top" arrow>
              <IconButton aria-label="save" onClick={() => {}}>
                <SaveIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete Prompt" placement="top" arrow>
              <IconButton aria-label="delete" onClick={handleDeletePrompt}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </div>
        </div>
      </Container>
      <Container component="div" className="p-1" maxWidth="xl" disableGutters>
        {prompt.messages.map((message) => (
          <MessageComponent
            key={message.id}
            id={message.id}
            parentId={prompt.id}
            type={message.type}
            defaultContent={message.content}
            content={message.content}
            dispatch={dispatch}
          />
        ))}
      </Container>
      <Container component="div" className="p-1" maxWidth="xl" disableGutters>
        <Paper elevation={2} className="p-1">
          <div>Output Field</div>
        </Paper>
      </Container>
    </div>
  );
};

export default Prompt;
