import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SendIcon from "@mui/icons-material/Send";
import { Box, Divider, Fab, IconButton, Paper, Stack, TextField, Tooltip, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";

import { ChatMessage, ThinkingIndicator, ToolCallIndicator } from "./ChatMessage";

import { DATA_TOUR } from "@/components/onboarding/data-tour";
import { useCompleteStep } from "@/components/onboarding/hooks/useCompleteStep";
import { useStepAction } from "@/components/onboarding/hooks/useStepAction";
import { getStepDemo, STEP_IDS } from "@/components/onboarding/steps";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useChatbot } from "@/hooks/useChatbot";

interface ChatbotDrawerProps {
  taskId: string;
}

export function ChatbotDrawer({ taskId }: ChatbotDrawerProps) {
  const { chatbotEnabled } = useDisplaySettings();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLElement>(null);
  const { messages, isStreaming, activeToolCall, sendMessage, clearConversation, abort } = useChatbot(taskId);
  const completeOpenChatStep = useCompleteStep(STEP_IDS.OPEN_CHAT);
  const completeSendMessageStep = useCompleteStep(STEP_IDS.SEND_MESSAGE);

  useStepAction(STEP_IDS.OPEN_CHAT, () => {
    setOpen(true);
    completeOpenChatStep();
  });

  useStepAction(STEP_IDS.SEND_MESSAGE, () => {
    const message = getStepDemo(STEP_IDS.SEND_MESSAGE)?.message;
    if (!message) return;
    setInput("");
    sendMessage(message);
    completeSendMessageStep();
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeToolCall]);

  if (!chatbotEnabled) return null;

  const handleOpen = () => {
    setOpen(true);
    completeOpenChatStep();
  };

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput("");
    sendMessage(trimmed);
    completeSendMessageStep();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {!open && (
        <Fab color="primary" onClick={handleOpen} sx={{ position: "fixed", bottom: 24, right: 24, zIndex: 1200 }} data-tour={DATA_TOUR.CHATBOT_FAB}>
          <ChatIcon />
        </Fab>
      )}

      {open && (
        <Paper
          elevation={8}
          sx={{
            position: "fixed",
            bottom: 24,
            right: 24,
            width: 380,
            height: 560,
            zIndex: 1200,
            display: "flex",
            flexDirection: "column",
            borderRadius: 3,
            overflow: "hidden",
          }}
          data-tour={DATA_TOUR.CHATBOT_PANEL}
        >
          <Stack sx={{ height: "100%" }}>
            {/* Header */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                px: 2,
                py: 1.5,
                bgcolor: "primary.main",
                color: "primary.contrastText",
              }}
            >
              <Typography variant="subtitle1" fontWeight={600}>
                Arthur AI Assistant
              </Typography>
              <Box>
                <Tooltip title="Clear conversation">
                  <IconButton size="small" onClick={clearConversation} sx={{ mr: 0.5, color: "primary.contrastText" }}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <IconButton size="small" onClick={() => setOpen(false)} sx={{ color: "primary.contrastText" }}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Box>
            </Box>

            {/* Messages */}
            <Box sx={{ flex: 1, overflowY: "auto", px: 2, py: 2 }}>
              {messages.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center", mt: 4 }}>
                  Ask me anything about your Arthur AI tasks, prompts, datasets, traces, or experiments.
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

            {/* Input */}
            <Box sx={{ px: 2, py: 1.5, display: "flex", gap: 1, alignItems: "flex-end" }}>
              <TextField
                variant="filled"
                fullWidth
                multiline
                maxRows={4}
                placeholder="Ask something..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isStreaming}
                size="small"
                hiddenLabel
              />
              <Tooltip title={isStreaming ? "Stop" : "Send"}>
                <IconButton color="primary" onClick={isStreaming ? abort : handleSend} disabled={!isStreaming && !input.trim()}>
                  {isStreaming ? <CloseIcon /> : <SendIcon />}
                </IconButton>
              </Tooltip>
            </Box>
          </Stack>
        </Paper>
      )}
    </>
  );
}
