import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Box, IconButton, Paper, Tooltip, Typography } from "@mui/material";

import { ChatPanel } from "./ChatPanel";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useChatbot } from "@/hooks/useChatbot";

/** Left offset that clears the fixed-width (w-64 = 256px) sidebar, so the
 * floating panel opens just beside the sidebar launcher button rather than
 * over the navigation. */
const SIDEBAR_CLEARANCE_PX = 272;

interface ChatbotDrawerProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
}

export function ChatbotDrawer({ taskId, open, onClose }: ChatbotDrawerProps) {
  const { chatbotEnabled } = useDisplaySettings();
  const { messages, isStreaming, activeToolCall, sendMessage, clearConversation, abort } = useChatbot(taskId);

  if (!chatbotEnabled) return null;

  return (
    <>
      {open && (
        <Paper
          elevation={8}
          sx={{
            position: "fixed",
            bottom: 24,
            left: SIDEBAR_CLEARANCE_PX,
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
                  <IconButton size="small" onClick={onClose} sx={{ color: "primary.contrastText" }}>
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
