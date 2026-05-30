import CloseIcon from "@mui/icons-material/Close";
import RefreshIcon from "@mui/icons-material/Refresh";
import SendIcon from "@mui/icons-material/Send";
import { Box, Divider, IconButton, Stack, TextField, Tooltip, Typography } from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatMessage, ThinkingIndicator, ToolCallIndicator } from "./ChatMessage";

import { useTaskTourFormPrefill, type TaskTourFormPrefill } from "@/features/task-tour/formPrefill";
import type { ChatMessage as ChatMessageType, ToolCallPayload } from "@/hooks/useChatbot";

interface ChatPanelProps {
  messages: ChatMessageType[];
  isStreaming: boolean;
  activeToolCall: ToolCallPayload | null;
  onSend: (message: string) => void;
  onAbort: () => void;
  onReset?: () => void;
  emptyStateText?: string;
  placeholder?: string;
  header?: React.ReactNode;
  inputMaxRows?: number;
  panelTourId?: string;
  inputTourId?: string;
}

export function ChatPanel({
  messages,
  isStreaming,
  activeToolCall,
  onSend,
  onAbort,
  onReset,
  emptyStateText = "Ask me anything about your Arthur AI tasks, prompts, datasets, traces, or experiments.",
  placeholder = "Ask something...",
  header,
  inputMaxRows = 4,
  panelTourId,
  inputTourId,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLElement>(null);
  const handleTourPrefill = useCallback((prefill: TaskTourFormPrefill) => {
    if (typeof prefill.value !== "string") return;
    const value = prefill.value;
    setInput((current) => (prefill.mode === "empty-only" && current.trim() ? current : value));
  }, []);

  useTaskTourFormPrefill(inputTourId, handleTourPrefill);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeToolCall]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput("");
    onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Stack data-tour-id={panelTourId} sx={{ height: "100%", minHeight: 0 }}>
      {header}

      <Box sx={{ flex: 1, overflowY: "auto", px: 2, py: 2 }}>
        {messages.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", mt: 4 }}>
            {emptyStateText}
          </Typography>
        )}
        {messages.map((msg, idx) => {
          if (msg.role === "assistant" && !msg.content) return null;
          return <ChatMessage key={idx} message={msg} />;
        })}
        {activeToolCall && <ToolCallIndicator toolCall={activeToolCall} />}
        {isStreaming &&
          !activeToolCall &&
          (() => {
            const last = [...messages].reverse().find((m) => m.role !== "tool_call");
            return !last?.content || last.role === "user";
          })() && <ThinkingIndicator />}
        <Box ref={messagesEndRef} />
      </Box>

      <Divider />

      <Box data-tour-id={inputTourId} sx={{ px: 2, py: 1.5, display: "flex", gap: 1, alignItems: "flex-end" }}>
        <TextField
          variant="filled"
          fullWidth
          multiline
          maxRows={inputMaxRows}
          placeholder={placeholder}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          size="small"
          hiddenLabel
        />
        <Tooltip title={isStreaming ? "Stop" : "Send"}>
          <IconButton color="primary" onClick={isStreaming ? onAbort : handleSend} disabled={!isStreaming && !input.trim()}>
            {isStreaming ? <CloseIcon /> : <SendIcon />}
          </IconButton>
        </Tooltip>
        {onReset && (
          <Tooltip title="Reset conversation" enterDelay={700} enterNextDelay={700}>
            <span>
              <IconButton color="primary" onClick={onReset} disabled={isStreaming || messages.length === 0}>
                <RefreshIcon />
              </IconButton>
            </span>
          </Tooltip>
        )}
      </Box>
    </Stack>
  );
}
