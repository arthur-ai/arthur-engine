import { Send, SmartToy, Person } from "@mui/icons-material";
import { Box, CircularProgress, IconButton, Paper, TextField, Typography } from "@mui/material";
import React, { useCallback, useEffect, useRef, useState } from "react";

import type { OpenAIMessageInput } from "@/lib/api-client/api-client";

interface SyntheticDataChatProps {
  conversation: OpenAIMessageInput[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
}

export const SyntheticDataChat: React.FC<SyntheticDataChatProps> = ({ conversation, isLoading, onSendMessage }) => {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [conversation, scrollToBottom]);

  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed && !isLoading) {
      onSendMessage(trimmed);
      setInputValue("");
    }
  }, [inputValue, isLoading, onSendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Messages area */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          p: 2,
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        {conversation.length === 0 && !isLoading && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "text.secondary",
            }}
          >
            <Typography variant="body2">The AI will respond here after generating data...</Typography>
          </Box>
        )}

        {conversation.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}

        {isLoading && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              Thinking...
            </Typography>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input area */}
      <Box
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            size="small"
            placeholder="Ask the AI to refine the data..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            sx={{
              "& .MuiOutlinedInput-root": {
                bgcolor: "background.default",
              },
            }}
          />
          <IconButton
            color="primary"
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            sx={{
              alignSelf: "flex-end",
            }}
          >
            <Send />
          </IconButton>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
          Try: "Add 5 more diverse rows", "Make the data more realistic", "Remove rows 3-5"
        </Typography>
      </Box>
    </Box>
  );
};

interface MessageBubbleProps {
  message: OpenAIMessageInput;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isAssistant = message.role === "assistant";
  const content = typeof message.content === "string" ? message.content : String(message.content);

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1,
        alignItems: "flex-start",
        flexDirection: isAssistant ? "row" : "row-reverse",
      }}
    >
      <Box
        sx={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: isAssistant ? "primary.main" : "grey.500",
          color: isAssistant ? "white" : "grey.700",
          flexShrink: 0,
        }}
      >
        {isAssistant ? <SmartToy fontSize="small" /> : <Person fontSize="small" />}
      </Box>
      <Paper
        elevation={0}
        sx={{
          p: 1.5,
          maxWidth: "85%",
          bgcolor: isAssistant ? "action.hover" : "primary.50",
          borderRadius: 2,
        }}
      >
        <Typography
          variant="body2"
          sx={{
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {content}
        </Typography>
      </Paper>
    </Box>
  );
};
