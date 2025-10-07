import React, { useCallback, useState } from "react";
import { PromptComponentProps } from "./types";
import MessageComponent from "./MessageComponent";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { providerEnum } from "./types";
// import { v4 as uuidv4 } from "uuid";

// const TEMP_ID = "user-defined-name-timestamp";
const PROVIDER_TEXT = "Provider";

// const newMessage = (
//   type: string = messageTypeEnum.USER,
//   content: string = ""
// ): MessageType => ({
//   id: TEMP_ID + (Math.random() * Math.random() * 1000).toString(), // TODO: use uuid
//   type,
//   content,
//   disabled: false,
// });

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 * A prompt should have a unique id: Name + timestamp. Can be used to hydrate.
 *
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
      <div className="grid grid-cols-2 gap-1">
        <div className="flex justify-start items-center gap-1">
          <h5>Prompt Header</h5>
          <div className="w-1/2">
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
        </div>
        <div className="flex justify-end items-center gap-1">
          <Button variant="contained" size="small" onClick={() => {}}>
            Save Prompt
          </Button>
          <Button variant="contained" size="small" onClick={handleDeletePrompt}>
            Delete Prompt
          </Button>
          <Button
            variant="contained"
            size="small"
            onClick={handleDuplicatePrompt}
          >
            Duplicate Prompt
          </Button>
        </div>
      </div>
      <div>
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
      </div>
      <div className="flex justify-end items-center">
        <Button variant="contained" size="small" onClick={handleAddMessage}>
          Add Message
        </Button>
      </div>
      <div>Output Field</div>
    </div>
  );
};

export default Prompt;
