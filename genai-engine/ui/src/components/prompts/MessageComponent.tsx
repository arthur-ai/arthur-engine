import React, { useState, useMemo, useCallback, useEffect } from "react";
import TextField from "@mui/material/TextField";
import { debounce } from "@mui/material/utils";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Button from "@mui/material/Button";
import { messageTypeEnum, MessageComponentProps } from "./types";

const LABEL_TEXT = "Message Type"; // Must be same for correct rendering

const Message: React.FC<MessageComponentProps> = ({
  id,
  type = messageTypeEnum.USER,
  defaultContent = "",
  onContentChange,
  onTypeChange,
  onDuplicate,
  onDelete,
}) => {
  const [inputValue, setInputValue] = useState(defaultContent);
  const [content, setContent] = useState(defaultContent);

  const handleTypeChange = useCallback(
    (event: SelectChangeEvent) => {
      onTypeChange(id, event.target.value);
    },
    [id, onTypeChange]
  );

  const handleMessageChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(event.target.value);
    },
    []
  );

  // Debounce the setMessage function to prevent excessive re-renders/API calls
  const debouncedSetMessage = useMemo(
    () =>
      debounce((value: string) => {
        // Empty strings are valid messages, but avoid propagating no-change events
        if (value === content) return;
        setContent(value);
      }, 500),
    [content]
  );

  useEffect(() => {
    onContentChange(id, content);
  }, [id, content, onContentChange]);

  useEffect(() => {
    debouncedSetMessage(inputValue);
  }, [inputValue, debouncedSetMessage]);

  return (
    <div className="bg-white rounded-lg shadow p-2">
      <div className="flex justify-between items-center">
        <FormControl sx={{ width: "25%" }} size="small">
          <InputLabel id="message-type">{LABEL_TEXT}</InputLabel>
          <Select
            labelId="message-type"
            id="message-type"
            label={LABEL_TEXT}
            value={type}
            onChange={handleTypeChange}
          >
            {Object.values(messageTypeEnum).map((typeValue) => (
              <MenuItem key={typeValue} value={typeValue}>
                {typeValue}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="contained" onClick={() => onDuplicate(id)}>
          Duplicate
        </Button>
        <Button variant="contained" onClick={() => onDelete(id)}>
          -
        </Button>
      </div>
      <div className="mt-1">
        <TextField
          id="message"
          variant="outlined"
          multiline
          maxRows={4}
          placeholder={type}
          value={inputValue}
          onChange={handleMessageChange}
          fullWidth
        />
      </div>
    </div>
  );
};

export default Message;
