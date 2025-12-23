import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";

import { usePromptPlaygroundStore } from "../stores/playground.store";
import { PromptType } from "../types";

import { useRenderUnsavedPrompt } from "@/hooks/useRenderUnsavedPrompt";

interface PreviewPromptModalProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  prompt: PromptType;
}

const PreviewPromptModal = ({ open, setOpen, prompt }: PreviewPromptModalProps) => {
  const keywords = usePromptPlaygroundStore((state) => state.keywords);

  const variables = Array.from(keywords.entries()).map(([name, value]) => ({
    name,
    value,
  }));

  const { data, error, isPending } = useRenderUnsavedPrompt({
    messages: prompt.messages,
    variables,
    enabled: open,
  });

  const renderedMessages = data?.messages || [];

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
        {isPending && (
          <Box sx={{ display: "flex", justifyContent: "center", padding: 3 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Box sx={{ padding: 2 }}>
            <Typography color="error">{error.message}</Typography>
          </Box>
        )}

        {!isPending && !error && renderedMessages.length === 0 && (
          <Box sx={{ padding: 2 }}>
            <Typography color="text.secondary">No messages to display</Typography>
          </Box>
        )}

        {!isPending && !error && renderedMessages.length > 0 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {renderedMessages.map((message, index) => (
              <Card key={index} variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1, textTransform: "capitalize" }}>
                    {message.role}
                  </Typography>
                  <Typography
                    variant="body1"
                    component="pre"
                    sx={{
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontFamily: "inherit",
                      margin: 0,
                    }}
                  >
                    {typeof message.content === "string" ? message.content : JSON.stringify(message.content, null, 2)}
                  </Typography>
                  {message.tool_calls && message.tool_calls.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                        Tool Calls
                      </Typography>
                      <Typography
                        variant="body2"
                        component="pre"
                        sx={{
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          fontFamily: "monospace",
                          fontSize: "0.875rem",
                          backgroundColor: "action.hover",
                          padding: 1,
                          borderRadius: 1,
                          margin: 0,
                        }}
                      >
                        {JSON.stringify(message.tool_calls, null, 2)}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default PreviewPromptModal;
