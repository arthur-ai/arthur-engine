import React, { useState, useCallback } from "react";
import { MessageType, messageTypeEnum } from "./types";
import MessageComponent from "./MessageComponent";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { providerEnum } from "./types";
// import { v4 as uuidv4 } from "uuid";

const TEMP_ID = "user-defined-name-timestamp";
const PROVIDER_TEXT = "Provider";

const newMessage = (
  type: string = messageTypeEnum.USER,
  content: string = ""
): MessageType => ({
  id: TEMP_ID + (Math.random() * Math.random() * 1000).toString(), // TODO: use uuid
  type,
  content,
});

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 * A prompt should have a unique id: Name + timestamp. Can be used to hydrate.
 *
 */
const Prompt = () => {
  const [messages, setMessages] = useState<Array<MessageType>>([]);

  const [provider, setProvider] = useState<string>(providerEnum.OPENAI);

  const handleProviderChange = (event: SelectChangeEvent) => {
    setProvider(event.target.value);
  };

  const addMessage = () => {
    setMessages([...messages, newMessage()]);
  };
  const deleteMessage = (id: string) => {
    setMessages(messages.filter((message) => message.id !== id));
  };
  const duplicateMessage = (id: string) => {
    const index = messages.findIndex((message) => message.id === id);
    const message = messages[index];
    const duplicateMessage = newMessage(message.type, message.content);
    const newArray = [
      ...messages.slice(0, index),
      duplicateMessage,
      ...messages.slice(index),
    ];

    setMessages(newArray);
  };

  const handleTypeChange = (id: string, type: string) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id ? { ...message, type } : message
      )
    );
  };
  const handleContentChange = useCallback((id: string, content: string) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id ? { ...message, content } : message
      )
    );
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center">
        <h5>Prompt Header</h5>
        <div className="w-1/4">
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
        <div>
          <Button variant="contained" onClick={addMessage}>
            +
          </Button>
        </div>
      </div>
      <div>
        {messages.map((message) => (
          <MessageComponent
            key={message.id}
            id={message.id}
            type={message.type}
            defaultContent={message.content}
            onTypeChange={handleTypeChange}
            onContentChange={handleContentChange}
            onDuplicate={duplicateMessage}
            onDelete={deleteMessage}
          />
        ))}
      </div>
      <div>Output Field</div>
    </div>
  );
};

export default Prompt;
