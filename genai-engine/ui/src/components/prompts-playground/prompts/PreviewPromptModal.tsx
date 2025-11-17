import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptType } from "../types";
import MessageComponent from "../messages/MessageComponent";

import { useRenderUnsavedPrompt } from "@/hooks/useRenderUnsavedPrompt";
import type { OpenAIMessageOutput } from "@/lib/api-client/api-client";

interface PreviewPromptModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  prompt: PromptType;
}

const PreviewPromptModal = ({ open, setOpen, prompt }: PreviewPromptModalProps) => {
  const { state } = usePromptContext();
  const [renderedMessages, setRenderedMessages] = useState<OpenAIMessageOutput[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const renderUnsavedPromptMutation = useRenderUnsavedPrompt();

  useEffect(() => {
    if (!open) {
      // Reset state when modal closes
      setRenderedMessages([]);
      setError(null);
      return;
    }

    // Fetch rendered prompt when modal opens
    const fetchRenderedPrompt = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Build variables array from state.keywords
        const variables = Array.from(state.keywords.entries()).map(([name, value]) => ({
          name,
          value,
        }));

        // Always use the unsaved prompt rendering endpoint
        // Send the messages directly from the current prompt state
        const rendered = await renderUnsavedPromptMutation.mutateAsync({
          messages: prompt.messages,
          variables,
        });

        setRenderedMessages(rendered.messages || []);
      } catch (err) {
        console.error("Failed to render prompt:", err);
        setError(err instanceof Error ? err.message : "Failed to render prompt");
      } finally {
        setIsLoading(false);
      }
    };

    fetchRenderedPrompt();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Typography variant="h6">Preview Rendered Prompt</Typography>
        <IconButton onClick={handleClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", padding: 3 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Box sx={{ padding: 2 }}>
            <Typography color="error">{error}</Typography>
          </Box>
        )}

        {!isLoading && !error && renderedMessages.length === 0 && (
          <Box sx={{ padding: 2 }}>
            <Typography color="text.secondary">No messages to display</Typography>
          </Box>
        )}

        {!isLoading && !error && renderedMessages.length > 0 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {renderedMessages.map((message, index) => (
              <Box
                key={index}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1,
                  backgroundColor: "background.paper",
                }}
              >
                <MessageComponent
                  id={`preview-${index}`}
                  parentId={`preview-parent`}
                  role={message.role}
                  defaultContent={message.content ?? ""}
                  content={message.content ?? ""}
                  toolCalls={message.tool_calls}
                />
              </Box>
            ))}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default PreviewPromptModal;
