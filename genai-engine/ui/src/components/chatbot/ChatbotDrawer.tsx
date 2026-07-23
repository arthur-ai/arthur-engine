import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Box, IconButton, Paper, Tooltip, Typography } from "@mui/material";

import { ChatPanel } from "./ChatPanel";

import { SIDEBAR_WIDTH_PX } from "@/constants/layout";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useChatbot } from "@/hooks/useChatbot";

/** Horizontal gap between the sidebar's right edge and the chat panel, so the
 * floating panel opens just beside the sidebar launcher rather than over the
 * navigation. */
const DRAWER_GAP_PX = 16;
/** Left offset that clears the sidebar. Derived from the shared sidebar width so
 * the two stay in sync if the sidebar is ever resized. */
const SIDEBAR_CLEARANCE_PX = SIDEBAR_WIDTH_PX + DRAWER_GAP_PX;

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
            bottom: 16,
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
