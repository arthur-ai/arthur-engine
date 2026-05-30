import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import { Avatar, Box, Button, Dialog, DialogActions, IconButton, Stack, Typography } from "@mui/material";

// Placeholder scheduling link. Swap for the real booking URL (Calendly/cal.com)
// once it exists — kept as a single constant so there's one spot to change.
const BOOKING_URL = "https://cal.com/arthur"; // TODO: replace with the real Agent Evals booking link

// Photo lives in `public/`, which Vite serves from the site root — referenced by
// absolute path rather than an `import` so it needs no bundler asset handling.
const CTO_AVATAR_SRC = "/cto-avatar.jpeg";
const CTO_NAME = "Zach Fry";
const CTO_TITLE = "CTO, Arthur";

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

        <Box>
          <Typography id="task-tour-cta-title" variant="h5" sx={{ fontWeight: 700 }}>
            Talk to our CTO about Agent Evals
          </Typography>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 0.5 }}>
            {CTO_NAME} · {CTO_TITLE}
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 420 }}>
          Grab 30 minutes to talk through agent evals for your team — from first guardrails to shipping with confidence.
        </Typography>

        {/* Placeholder for the future embedded booking calendar. For now it frames
            the primary "Book a time" action; drop the calendar embed in here later. */}
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
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
            Booking calendar coming soon
          </Typography>
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
