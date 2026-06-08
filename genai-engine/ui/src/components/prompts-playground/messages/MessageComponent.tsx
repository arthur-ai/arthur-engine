import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { debounce } from "@mui/material/utils";
import React, { useState, useMemo, useCallback, useEffect } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { MESSAGE_ROLE_OPTIONS, MessageComponentProps } from "../types";

import { HighlightedInputComponent } from "./HighlightedInputComponent";

import { OpenAIMessageItem, ToolCall } from "@/lib/api-client/api-client";

const DEBOUNCE_TIME = 500;
const LABEL_TEXT = "Message Role"; // Must be same for correct rendering

type AssistantMessageMode = "message" | "toolCall";

// A single editable tool call draft. arguments is kept as a raw string so the user
// can type freely (and use {{variables}}); it is parsed/validated on commit.
interface ToolCallDraft {
  id: string;
  name: string;
  arguments: string;
}

const EMPTY_TOOL_CALL_DRAFT: ToolCallDraft = { id: "", name: "", arguments: "" };

// Convert backend ToolCall[] into editable drafts.
const toolCallsToDrafts = (calls: ToolCall[] | null | undefined): ToolCallDraft[] => {
  if (!calls || calls.length === 0) {
    return [{ ...EMPTY_TOOL_CALL_DRAFT }];
  }
  return calls.map((call) => ({
    id: call.id ?? "",
    name: call.function?.name ?? "",
    arguments: call.function?.arguments ?? "",
  }));
};

// Convert drafts back into backend ToolCall[], dropping fully-empty drafts.
const draftsToToolCalls = (drafts: ToolCallDraft[]): ToolCall[] => {
  return drafts
    .filter((draft) => draft.id.trim() || draft.name.trim() || draft.arguments.trim())
    .map((draft) => ({
      id: draft.id.trim(),
      type: "function",
      function: {
        name: draft.name.trim(),
        arguments: draft.arguments,
      },
    }));
};

const Message: React.FC<MessageComponentProps> = ({ id, parentId, role, defaultContent = "", content, toolCalls, toolCallId, dragHandleProps }) => {
  const { dispatch } = usePromptContext();
  const [inputValue, setInputValue] = useState(defaultContent);
  const [toolCallDrafts, setToolCallDrafts] = useState<ToolCallDraft[]>(() => toolCallsToDrafts(toolCalls));
  const [toolCallIdValue, setToolCallIdValue] = useState(toolCallId ?? "");
  const [assistantMode, setAssistantMode] = useState<AssistantMessageMode>(toolCalls && toolCalls.length > 0 ? "toolCall" : "message");

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

  const handleToolCallFieldChange = useCallback((index: number, field: keyof ToolCallDraft, value: string) => {
    setToolCallDrafts((prev) => prev.map((draft, i) => (i === index ? { ...draft, [field]: value } : draft)));
  }, []);

  const handleAddToolCall = useCallback(() => {
    setToolCallDrafts((prev) => [...prev, { ...EMPTY_TOOL_CALL_DRAFT }]);
  }, []);

  const handleRemoveToolCall = useCallback((index: number) => {
    setToolCallDrafts((prev) => {
      const next = prev.filter((_, i) => i !== index);
      // Always keep at least one (empty) draft so the editor never collapses.
      return next.length > 0 ? next : [{ ...EMPTY_TOOL_CALL_DRAFT }];
    });
  }, []);

  const handleToolCallIdChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setToolCallIdValue(event.target.value);
  }, []);

  const handleAssistantModeChange = useCallback(
    (_event: React.MouseEvent<HTMLElement>, newMode: AssistantMessageMode | null) => {
      if (!newMode || newMode === assistantMode) return;
      // Toggling is only a view switch — it must not destroy the text content or the
      // tool call drafts. Both are kept locally; only the active mode is committed.
      setAssistantMode(newMode);
    },
    [assistantMode]
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

  // An assistant message is either a text message or a tool call — never both. The
  // active toggle (assistantMode) decides which one is committed to state; the other
  // is kept locally so an accidental toggle doesn't lose what was typed, but it is not
  // saved. For non-assistant roles there is no toggle, so content is always committed.
  const isToolCallMode = role === "assistant" && assistantMode === "toolCall";

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
      debounce((drafts: ToolCallDraft[]) => {
        const calls = draftsToToolCalls(drafts);
        dispatch({
          type: "editMessageToolCalls",
          payload: {
            parentId,
            id,
            toolCalls: calls.length > 0 ? calls : null,
          },
        });
      }, DEBOUNCE_TIME),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [parentId, id]
  );

  // Debounce tool_call_id updates (only relevant for `tool` role messages)
  const debouncedSetToolCallId = useMemo(
    () =>
      debounce((value: string) => {
        dispatch({
          type: "editMessageToolCallId",
          payload: { parentId, id, toolCallId: value.trim() ? value.trim() : null },
        });
      }, DEBOUNCE_TIME),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [parentId, id]
  );

  useEffect(() => {
    if (role === "tool") {
      debouncedSetToolCallId(toolCallIdValue);
    } else if (toolCallId) {
      // Role changed away from `tool`; drop the stale id so it isn't saved.
      dispatch({ type: "editMessageToolCallId", payload: { parentId, id, toolCallId: null } });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, toolCallIdValue, debouncedSetToolCallId]);

  // Commit only the active mode's value; null out the inactive one so a message
  // never carries both content and tool calls into state / save.
  useEffect(() => {
    if (isToolCallMode) {
      debouncedSetToolCalls(toolCallDrafts);
      if (content) {
        dispatch({ type: "editMessage", payload: { parentId, id, content: "" } });
      }
    } else {
      debouncedSetMessage(inputValue);
      if (toolCalls && toolCalls.length > 0) {
        dispatch({ type: "editMessageToolCalls", payload: { parentId, id, toolCalls: null } });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isToolCallMode, inputValue, toolCallDrafts, debouncedSetMessage, debouncedSetToolCalls]);

  // Seed the drafts from the toolCalls prop only on mount (e.g. when loading from a
  // trace). After mount, local drafts are the source of truth so editing isn't
  // clobbered by the round-trip back through the dispatched prop.
  useEffect(() => {
    if (toolCalls && toolCalls.length > 0) {
      setToolCallDrafts(toolCallsToDrafts(toolCalls));
      setAssistantMode("toolCall");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      {role === "assistant" && (
        <Box sx={{ mt: 2, display: "flex", justifyContent: "flex-start" }}>
          <ToggleButtonGroup size="small" exclusive value={assistantMode} onChange={handleAssistantModeChange} aria-label="assistant message type">
            <ToggleButton value="message" aria-label="regular message">
              Message
            </ToggleButton>
            <ToggleButton value="toolCall" aria-label="tool call">
              Tool Call
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}
      {role === "tool" && (
        <Box sx={{ mt: 2 }}>
          <TextField
            label="Tool Call ID"
            placeholder="Must match a tool_call id from the assistant message"
            value={toolCallIdValue}
            onChange={handleToolCallIdChange}
            variant="outlined"
            size="small"
            fullWidth
            sx={{ backgroundColor: "background.paper" }}
          />
        </Box>
      )}
      <Box sx={{ mt: 2 }}>
        {isToolCallMode ? (
          <Stack spacing={1.5}>
            {toolCallDrafts.map((draft, index) => (
              <Box
                key={index}
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 1.5,
                  backgroundColor: "background.paper",
                }}
              >
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Tool Call {index + 1}
                  </Typography>
                  <Tooltip title="Remove tool call" placement="top-start" arrow>
                    <IconButton aria-label="remove tool call" size="small" onClick={() => handleRemoveToolCall(index)}>
                      <DeleteIcon fontSize="small" color="error" />
                    </IconButton>
                  </Tooltip>
                </Box>
                <Stack spacing={1.5}>
                  <TextField
                    label="Tool Call ID"
                    placeholder="tool_call_id"
                    value={draft.id}
                    onChange={(event) => handleToolCallFieldChange(index, "id", event.target.value)}
                    variant="outlined"
                    size="small"
                    fullWidth
                    sx={{ backgroundColor: "background.paper", "& .MuiInputBase-input": { fontSize: "0.8125rem", fontFamily: "monospace" } }}
                  />
                  <TextField
                    label="Function name"
                    placeholder="get_weather"
                    value={draft.name}
                    onChange={(event) => handleToolCallFieldChange(index, "name", event.target.value)}
                    variant="outlined"
                    size="small"
                    fullWidth
                    sx={{ backgroundColor: "background.paper", "& .MuiInputBase-input": { fontSize: "0.8125rem", fontFamily: "monospace" } }}
                  />
                  <HighlightedInputComponent
                    value={draft.arguments}
                    onChange={(event) => handleToolCallFieldChange(index, "arguments", event.target.value)}
                    placeholder={'{ "argument_name": "argument_value" }'}
                  />
                </Stack>
              </Box>
            ))}
            <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
              <Button variant="text" size="small" startIcon={<AddIcon />} onClick={handleAddToolCall}>
                Add tool call
              </Button>
            </Box>
          </Stack>
        ) : (
          <HighlightedInputComponent value={inputValue} onChange={handleContentChange} />
        )}
      </Box>
    </div>
  );
};

export default Message;
