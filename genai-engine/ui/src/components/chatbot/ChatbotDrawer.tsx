import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Box, Fab, IconButton, Paper, Tooltip, Typography } from "@mui/material";
import { useState } from "react";

import { ChatPanel } from "./ChatPanel";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useChatbot } from "@/hooks/useChatbot";

interface ChatbotDrawerProps {
  taskId: string;
}

export function ChatbotDrawer({ taskId }: ChatbotDrawerProps) {
  const { chatbotEnabled } = useDisplaySettings();
  const [open, setOpen] = useState(false);
  const { messages, isStreaming, activeToolCall, sendMessage, clearConversation, abort } = useChatbot(taskId);

  if (!chatbotEnabled) return null;

  return (
    <>
      {!open && (
        <Fab color="primary" onClick={() => setOpen(true)} sx={{ position: "fixed", bottom: 24, right: 24, zIndex: 1200 }}>
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
        >
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            activeToolCall={activeToolCall}
            onSend={sendMessage}
            onAbort={abort}
            header={
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
            }
          />
        </Paper>
      )}
    </>
  );
}
