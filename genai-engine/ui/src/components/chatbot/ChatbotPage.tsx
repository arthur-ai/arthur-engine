import { Box, Stack, Typography } from "@mui/material";
import { useCallback } from "react";
import { useParams } from "react-router-dom";

import { ChatPanel } from "@/components/chatbot/ChatPanel";
import { dispatchTourEvent, TASK_TOUR_ACTIONS, TOUR_IDS } from "@/features/task-tour";
import { useChatbot } from "@/hooks/useChatbot";

export function ChatbotPage() {
  const { id: taskId } = useParams<{ id: string }>();
  const { messages, isStreaming, activeToolCall, sendMessage, clearConversation, abort } = useChatbot(taskId ?? "", {
    variant: "demo",
  });
  const handleSendMessage = useCallback(
    (message: string) => {
      sendMessage(message);
      dispatchTourEvent(TASK_TOUR_ACTIONS.demoAgentMessageSent);
    },
    [sendMessage]
  );

  if (!taskId) return null;

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.default",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              Demo Agent
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Chat with the demo agent. It answers general-knowledge questions by searching and fetching Wikipedia articles.
            </Typography>
          </Box>
        </Stack>
      </Box>

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          activeToolCall={activeToolCall}
          onSend={handleSendMessage}
          onAbort={abort}
          onReset={clearConversation}
          emptyStateText="Ask the demo agent any general-knowledge question. It can search and fetch Wikipedia articles."
          placeholder="Ask the demo agent..."
          inputMaxRows={8}
          panelTourId={TOUR_IDS.chatWindow}
          inputTourId={TOUR_IDS.chatSendPlaceholder}
        />
      </Box>
    </Box>
  );
}
