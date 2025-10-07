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
import { messageRoleEnum, MessageComponentProps } from "./types";
import Paper from "@mui/material/Paper";
import extractMustacheKeywords from "./mustacheExtractor";

const DEBOUNCE_TIME = 500;
const LABEL_TEXT = "Message Role"; // Must be same for correct rendering

const Message: React.FC<MessageComponentProps> = ({
  id,
  parentId,
  role,
  defaultContent = "",
  content,
  dispatch,
}) => {
  const [inputValue, setInputValue] = useState(defaultContent);

  const handleRoleChange = useCallback(
    (event: SelectChangeEvent) => {
      const selectedRole = event.target.value;
      if (selectedRole === role) return;

      dispatch({
        type: "changeMessageRole",
        payload: { id, role: selectedRole, parentId },
      });
    },
    [id, dispatch, role, parentId]
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

  // When the content changes, whether by user or hydration, update the keyword values
  useEffect(() => {
    dispatch({
      type: "updateKeywords",
      payload: {
        id,
        messageKeywords: extractMustacheKeywords(content).keywords,
      },
    });

    // Handle keyword tracking cleanup when message or prompt is deleted
    return () => {
      dispatch({
        type: "updateKeywords",
        payload: { id, messageKeywords: [] },
      });
    };
  }, [id, content, dispatch]);

  return (
    <Paper elevation={2} className="m-1 p-2">
      <div className="grid grid-cols-2 gap-1">
        <div className="flex justify-start items-center">
          <FormControl sx={{ width: "50%" }} size="small">
            <InputLabel id={`message-role-${id}`}>{LABEL_TEXT}</InputLabel>
            <Select
              labelId={`message-role-${id}`}
              id={`message-role-${id}`}
              label={LABEL_TEXT}
              value={role}
              onChange={handleRoleChange}
            >
              {Object.values(messageRoleEnum).map((roleValue) => (
                <MenuItem key={roleValue} value={roleValue}>
                  {roleValue}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </div>
        <div className="flex justify-end items-center">
          <Tooltip title="Duplicate Message" placement="top-start" arrow>
            <IconButton
              aria-label="duplicate message"
              onClick={handleDuplicate}
            >
              <ContentCopyIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete Message" placement="top-start" arrow>
            <IconButton aria-label="delete message" onClick={handleDelete}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </div>
      </div>
      <div className="mt-2">
        <TextField
          id={`message-${id}-input`}
          label="Content"
          variant="outlined"
          maxRows={4}
          placeholder={role}
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
