import React, { useState, useMemo, useCallback, useEffect } from "react";
import TextField from "@mui/material/TextField";
import { debounce } from "@mui/material/utils";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import Tooltip from "@mui/material/Tooltip";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { messageTypeEnum, MessageComponentProps } from "./types";
import Paper from "@mui/material/Paper";

const DEBOUNCE_TIME = 500;
const LABEL_TEXT = "Message Type"; // Must be same for correct rendering

const Message: React.FC<MessageComponentProps> = ({
  id,
  parentId,
  type,
  defaultContent = "",
  content,
  dispatch,
}) => {
  const [inputValue, setInputValue] = useState(defaultContent);

  const handleTypeChange = useCallback(
    (event: SelectChangeEvent) => {
      const selectedType = event.target.value;
      if (selectedType === type) return;

      dispatch({
        type: "changeMessageType",
        payload: { id, type: selectedType, parentId },
      });
    },
    [id, dispatch, type, parentId]
  );

  const handleContentChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(event.target.value);
    },
    []
  );

  const handleDuplicate = useCallback(() => {
    dispatch({
      type: "duplicateMessage",
      payload: { parentId, id },
    });
  }, [dispatch, parentId, id]);

  const handleDelete = useCallback(() => {
    dispatch({
      type: "deleteMessage",
      payload: { parentId, id },
    });
  }, [dispatch, parentId, id]);

  // Debounce the setMessage function to prevent excessive re-renders/API calls
  const debouncedSetMessage = useMemo(
    () =>
      debounce((value: string) => {
        // Empty strings are valid messages, but avoid propagating no-change events
        if (value === content) return;
        dispatch({
          type: "editMessage",
          payload: { parentId, id, content: value },
        });
      }, DEBOUNCE_TIME),
    [content, parentId, id, dispatch]
  );

  useEffect(() => {
    debouncedSetMessage(inputValue);
  }, [inputValue, debouncedSetMessage]);

  return (
    <Paper elevation={2} className="p-2">
      <div className="grid grid-cols-2 gap-1">
        <div className="flex justify-start items-center">
          <FormControl sx={{ width: "50%" }} size="small">
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
        </div>
        <div className="flex justify-end items-center">
          <Tooltip title="Duplicate Message" placement="top" arrow>
            <IconButton
              aria-label="duplicate message"
              onClick={handleDuplicate}
            >
              <ContentCopyIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete Message" placement="top" arrow>
            <IconButton aria-label="delete message" onClick={handleDelete}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </div>
      </div>
      <div className="mt-1">
        <TextField
          id="message"
          variant="outlined"
          maxRows={4}
          placeholder={type}
          value={inputValue}
          onChange={handleContentChange}
          type="text"
          fullWidth
          multiline
        />
      </div>
    </Paper>
  );
};

export default Message;
