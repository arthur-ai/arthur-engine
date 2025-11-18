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

import { usePromptContext } from "../PromptsPlaygroundContext";
import { MESSAGE_ROLE_OPTIONS, MessageComponentProps } from "../types";

import { HighlightedInputComponent } from "./HighlightedInputComponent";

import { OpenAIMessageItem } from "@/lib/api-client/api-client";

const DEBOUNCE_TIME = 500;
const LABEL_TEXT = "Message Role"; // Must be same for correct rendering

const Message: React.FC<MessageComponentProps> = ({ id, parentId, role, defaultContent = "", content, toolCalls, dragHandleProps }) => {
  const { dispatch } = usePromptContext();
  const [inputValue, setInputValue] = useState(defaultContent);
  const [toolCallsValue, setToolCallsValue] = useState(toolCalls && toolCalls.length > 0 ? JSON.stringify(toolCalls, null, 2) : "");

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

  const handleContentChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  }, []);

  const handleToolCallsChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setToolCallsValue(event.target.value);
  }, []);

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
      debounce((value: string | OpenAIMessageItem[]) => {
        // Empty strings are valid messages, but avoid propagating no-change events
        if (value === content) return;
        dispatch({
          type: "editMessage",
          payload: {
            parentId,
            id,
            content: typeof value === "string" ? value : value.map((item) => item.text || "").join(" "),
          },
        });
      }, DEBOUNCE_TIME),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [content, parentId, id]
  );

  // Debounce tool calls updates
  const debouncedSetToolCalls = useMemo(
    () =>
      debounce((value: string) => {
        try {
          const parsed = value.trim() ? JSON.parse(value) : null;
          dispatch({
            type: "editMessageToolCalls",
            payload: {
              parentId,
              id,
              toolCalls: parsed,
            },
          });
        } catch (error) {
          // Invalid JSON - don't update
          console.error("Invalid tool calls JSON:", error);
        }
      }, DEBOUNCE_TIME),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [parentId, id]
  );

  useEffect(() => {
    debouncedSetMessage(inputValue);
  }, [inputValue, debouncedSetMessage]);

  useEffect(() => {
    debouncedSetToolCalls(toolCallsValue);
  }, [toolCallsValue, debouncedSetToolCalls]);

  // Sync toolCallsValue when toolCalls prop changes (e.g., when loading from trace)
  useEffect(() => {
    if (toolCalls && toolCalls.length > 0) {
      const newValue = JSON.stringify(toolCalls, null, 2);
      if (newValue !== toolCallsValue) {
        setToolCallsValue(newValue);
      }
    }
  }, [toolCalls, toolCallsValue]);

  return (
    <div className="p-2">
      <div className="grid grid-cols-2 gap-1">
        <div className="flex justify-start items-center">
          <FormControl sx={{ width: "50%" }} size="small">
            <InputLabel id={`message-role-${id}`}>{LABEL_TEXT}</InputLabel>
            <Select labelId={`message-role-${id}`} id={`message-role-${id}`} label={LABEL_TEXT} value={role} onChange={handleRoleChange}>
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
            <IconButton aria-label="drag handle" sx={{ cursor: "grab" }} {...dragHandleProps}>
              <DragIndicatorIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Duplicate Message" placement="top-start" arrow>
            <IconButton aria-label="duplicate message" onClick={handleDuplicate}>
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
        {toolCalls && toolCalls.length > 0 && (!content || content === "") ? (
          <HighlightedInputComponent value={toolCallsValue} onChange={handleToolCallsChange} label="Tool Calls (JSON)" />
        ) : (
          <HighlightedInputComponent value={inputValue} onChange={handleContentChange} label="Content" />
        )}
      </div>
    </div>
  );
};

export default Message;
