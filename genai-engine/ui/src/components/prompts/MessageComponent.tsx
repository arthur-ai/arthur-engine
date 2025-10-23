import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import Tooltip from "@mui/material/Tooltip";
import { debounce } from "@mui/material/utils";
import React, { useState, useMemo, useCallback, useEffect } from "react";

import { HighlightedInputComponent } from "./HighlightedInputComponent";
import extractMustacheKeywords from "./mustacheExtractor";
import { usePromptContext } from "./PromptContext";
import { MESSAGE_ROLE_OPTIONS, MessageComponentProps } from "./types";

const DEBOUNCE_TIME = 500;
const LABEL_TEXT = "Message Role"; // Must be same for correct rendering

const Message: React.FC<MessageComponentProps> = ({
  id,
  parentId,
  role,
  defaultContent = "",
  content,
  dragHandleProps,
}) => {
  const { dispatch } = usePromptContext();
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [id, role, parentId]
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parentId, id]);

  const handleDelete = useCallback(() => {
    dispatch({
      type: "deleteMessage",
      payload: { parentId, id },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parentId, id]);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [content, parentId, id]
  );

  useEffect(() => {
    debouncedSetMessage(inputValue);
  }, [inputValue, debouncedSetMessage]);

  // When the content changes, whether by user or hydration, update the keyword values
  useEffect(() => {
    const extractedKeywords = extractMustacheKeywords(content).keywords;

    if (extractedKeywords.length > 0) {
      dispatch({
        type: "updateKeywords",
        payload: { id, messageKeywords: extractedKeywords },
      });
    }

    // Handle keyword tracking cleanup when message or prompt is deleted
    return () => {
      dispatch({
        type: "updateKeywords",
        payload: { id, messageKeywords: [] },
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, content]);

  return (
    <div className="p-2">
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
              {MESSAGE_ROLE_OPTIONS.map((roleValue) => (
                <MenuItem key={roleValue} value={roleValue}>
                  {roleValue.charAt(0).toUpperCase() + roleValue.slice(1)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </div>
        <div className="flex justify-end items-center">
          <Tooltip title="Drag to reorder" placement="top-start" arrow>
            <IconButton
              aria-label="drag handle"
              sx={{ cursor: "grab" }}
              {...dragHandleProps}
            >
              <DragIndicatorIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Duplicate Message" placement="top-start" arrow>
            <IconButton
              aria-label="duplicate message"
              onClick={handleDuplicate}
            >
              <ContentCopyIcon color="secondary" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete Message" placement="top-start" arrow>
            <IconButton aria-label="delete message" onClick={handleDelete}>
              <DeleteIcon color="error" />
            </IconButton>
          </Tooltip>
        </div>
      </div>
      <div className="mt-2">
        <HighlightedInputComponent
          value={inputValue}
          onChange={handleContentChange}
          label="Content"
          placeholder={role}
        />
      </div>
    </div>
  );
};

export default Message;
