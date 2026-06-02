import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import { Avatar, Box, Button, Dialog, DialogActions, IconButton, Stack, Typography } from "@mui/material";

// Scheduling link for booking time with Arthur's CTO to talk Agent Evals.
// Kept as a single constant so there's one spot to change.
const BOOKING_URL = "https://calendar.app.google/aRT3BnbUabjQRdJE6";

// Photo lives in `public/`, which Vite serves from the site root — referenced by
// absolute path rather than an `import` so it needs no bundler asset handling.
const CTO_AVATAR_SRC = "/cto-avatar.jpeg";
const CTO_NAME = "Zach Fry";

export interface CtaDialogProps {
  open: boolean;
  onDismiss: () => void;
}

/**
 * Post-certificate call-to-action: invites the user to book time with Arthur's
 * CTO to talk Agent Evals. Shown by `CertificateWidget` after the completion
 * certificate is closed, as the final beat of the tour.
 */
export function CtaDialog({ open, onDismiss }: CtaDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onDismiss}
      maxWidth="sm"
      fullWidth
      aria-labelledby="task-tour-cta-title"
      slotProps={{ paper: { sx: { borderRadius: 3, position: "relative" } } }}
    >
      <IconButton
        size="small"
        onClick={onDismiss}
        aria-label="Dismiss call to action"
        sx={{
          position: "absolute",
          top: 12,
          right: 12,
          color: "text.secondary",
          "&:hover": { color: "text.primary", bgcolor: "action.hover" },
        }}
      >
        <CloseIcon sx={{ fontSize: 18 }} />
      </IconButton>

      <Stack spacing={2.5} alignItems="center" sx={{ px: { xs: 3, md: 5 }, pt: 5, pb: 3, textAlign: "center" }}>
        <Avatar src={CTO_AVATAR_SRC} alt={CTO_NAME} sx={{ width: 72, height: 72 }}>
          ZF
        </Avatar>

        <Typography id="task-tour-cta-title" variant="h5" sx={{ fontWeight: 700 }}>
          Hi, I’m Zach, the CTO at Arthur
        </Typography>

        <Stack spacing={1.5} sx={{ maxWidth: 420, textAlign: "left" }}>
          <Typography variant="body2" color="text.secondary">
            If you found this exercise useful and have a need to build strongly performant and production-ready agents,
            book time on my calendar. We’ve helped many teams, from scrappy startups to large Fortune 100 companies, by
            providing the tools and techniques to ensure trustworthy and reliable AI systems.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Look forward to chatting.
          </Typography>
          <Typography variant="subtitle2" color="text.secondary" sx={{ textAlign: "right", fontStyle: "italic" }}>
            — {CTO_NAME}
          </Typography>
        </Stack>

        {/* Frames the primary "Book a time" action; a calendar embed can drop in here later. */}
        <Box
          sx={{
            width: "100%",
            maxWidth: 420,
            border: 1,
            borderColor: "divider",
            borderRadius: 2,
            bgcolor: "action.hover",
            px: 3,
            py: 3,
          }}
        >
          <Button
            variant="contained"
            href={BOOKING_URL}
            target="_blank"
            rel="noopener noreferrer"
            endIcon={<ArrowForwardIcon sx={{ fontSize: 18 }} />}
          >
            Book a time
          </Button>
        </Box>
      </Stack>

      <DialogActions sx={{ justifyContent: "center", pb: 2.5 }}>
        <Button variant="text" color="inherit" onClick={onDismiss}>
          Dismiss
        </Button>
      </DialogActions>
    </Dialog>
  );
}
