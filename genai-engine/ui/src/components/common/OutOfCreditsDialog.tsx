// UP-4390: rendered at the app shell, opened by any call site that detects
// a 402 TOKEN_LIMIT_EXCEEDED response from the engine. Centralises the
// "contact Arthur" message so we don't ship a different copy per surface.

import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import React from "react";

import { useOutOfCreditsDialog } from "@/contexts/OutOfCreditsContext";

const formatTokenCount = (n: number | null | undefined): string => {
  if (typeof n !== "number") return "—";
  return n.toLocaleString();
};

export const OutOfCreditsDialog: React.FC = () => {
  const { isOpen, detail, dismiss } = useOutOfCreditsDialog();

  return (
    <Dialog
      open={isOpen}
      onClose={dismiss}
      maxWidth="sm"
      fullWidth
      aria-labelledby="out-of-credits-dialog-title"
      aria-describedby="out-of-credits-dialog-description"
    >
      <DialogTitle id="out-of-credits-dialog-title">
        <Stack direction="row" alignItems="center" spacing={1}>
          <WarningAmberIcon sx={{ color: "warning.main" }} />
          <Typography variant="h6" component="span">
            Out of LLM credits
          </Typography>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Typography id="out-of-credits-dialog-description" variant="body1" sx={{ mb: detail ? 2 : 0 }}>
          {detail?.message ?? "Your organization has used all available LLM credits. " + "Contact Arthur to purchase more."}
        </Typography>
        {detail && (
          <Box
            sx={{
              bgcolor: "action.hover",
              borderRadius: 1,
              p: 2,
              fontFamily: "monospace",
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Used: {formatTokenCount(detail.tokens_used)} tokens
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Limit: {formatTokenCount(detail.tokens_limit)} tokens
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={dismiss} variant="contained" autoFocus>
          OK
        </Button>
      </DialogActions>
    </Dialog>
  );
};
