import { Box, Stack, Typography } from "@mui/material";
import { useParams } from "react-router-dom";

import { ChatPanel } from "@/components/chatbot/ChatPanel";
import { useChatbot } from "@/hooks/useChatbot";

export function ChatbotPage() {
  const { id: taskId } = useParams<{ id: string }>();
  const { messages, isStreaming, activeToolCall, sendMessage, clearConversation, abort } = useChatbot(taskId ?? "", {
    variant: "demo",
  });

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
              Chatbot
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Chat with the demo agent. It can search and fetch Wikipedia articles.
            </Typography>
          </Box>
        </Stack>
      </Box>

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          activeToolCall={activeToolCall}
          onSend={sendMessage}
          onAbort={abort}
          onReset={clearConversation}
          emptyStateText="Ask the demo chatbot any general knowledge questions. It can search and fetch Wikipedia articles."
          placeholder="Ask the demo chatbot..."
          inputMaxRows={8}
        />
      </Box>
    </Box>
  );
}
