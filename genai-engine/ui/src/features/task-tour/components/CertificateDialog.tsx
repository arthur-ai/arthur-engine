import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import { Box, Button, Dialog, IconButton, Paper, Stack, Typography, useTheme } from "@mui/material";

export interface CertificateDialogProps {
  open: boolean;
  /** Display name shown on the certificate. Falls back to a generic recipient. */
  recipientName?: string;
  /** Workspace label, e.g. "arthur-engine · prod". */
  workspaceLabel?: string;
  /** Pre-formatted issue date. Defaults to today, rendered as `MMM D, YYYY`. */
  issuedOn?: string;
  onClose: () => void;
}

function formatToday(): string {
  return new Date().toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Completion dialog shown on `tour:end{reason:"completed"}`. Mirrors the
 * design's certificate-screen layout (Evals 101 wordmark, recipient name in
 * brand purple, issued metadata, big green check) but renders as a modal
 * rather than a dedicated route so it overlays whichever task page the user
 * happens to be on when they finish the tour.
 */
export function CertificateDialog({
  open,
  recipientName = "you",
  workspaceLabel = "Arthur",
  issuedOn = formatToday(),
  onClose,
}: CertificateDialogProps) {
  const theme = useTheme();

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="task-tour-certificate-title"
      slotProps={{
        paper: {
          elevation: 16,
          sx: { borderRadius: 4, overflow: "visible", position: "relative" },
        },
      }}
    >
      <IconButton
        size="small"
        onClick={onClose}
        aria-label="Dismiss certificate"
        sx={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 2,
          color: "text.secondary",
          "&:hover": { color: "text.primary", bgcolor: "action.hover" },
        }}
      >
        <CloseIcon sx={{ fontSize: 18 }} />
      </IconButton>

      <Paper
        elevation={0}
        sx={{
          position: "relative",
          py: 7,
          px: { xs: 4, md: 8 },
          textAlign: "center",
          backgroundImage: `radial-gradient(circle at 12% 12%, ${theme.palette.secondary.light}33, transparent 40%), radial-gradient(circle at 88% 88%, ${theme.palette.primary.light}33, transparent 40%)`,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: "secondary.main",
            letterSpacing: 3,
            textTransform: "uppercase",
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          Certificate of Completion
        </Typography>
        <Typography id="task-tour-certificate-title" variant="h3" sx={{ fontWeight: 700, mt: 1.5, mb: 2.5, letterSpacing: -1 }}>
          Evals 101
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          Awarded to
        </Typography>
        <Typography
          variant="h2"
          sx={{
            fontWeight: 700,
            color: "secondary.main",
            mt: 1,
            mb: 3,
            letterSpacing: -1.5,
            fontSize: { xs: 32, md: 52 },
          }}
        >
          {recipientName}
        </Typography>
        <Box sx={{ width: 360, height: "1px", bgcolor: "divider", mx: "auto", mb: 3.5 }} />
        <Typography variant="body1" sx={{ color: "text.secondary", lineHeight: 1.65, maxWidth: 480, mx: "auto" }}>
          For successfully completing the Arthur Development Lifecycle walkthrough — measuring agent quality with continuous evals, debugging failures
          with traces, and shipping tested updates with confidence.
        </Typography>

        <Stack direction="row" spacing={3} justifyContent="center" sx={{ mt: 3.5, flexWrap: "wrap" }}>
          {[
            ["Issued", issuedOn],
            ["Workspace", workspaceLabel],
            ["Course", "Evals 101 (v1)"],
          ].map(([k, v]) => (
            <Box key={k}>
              <Typography variant="caption" sx={{ color: "text.disabled", display: "block" }}>
                {k}
              </Typography>
              <Typography variant="caption" sx={{ color: "text.primary", fontWeight: 600 }}>
                {v}
              </Typography>
            </Box>
          ))}
        </Stack>

        <Stack direction="row" spacing={1.5} justifyContent="center" sx={{ mt: 4 }}>
          <Button variant="contained" onClick={onClose}>
            Back to task
          </Button>
        </Stack>

        <Box
          sx={{
            position: "absolute",
            bottom: -32,
            right: { xs: 32, md: 64 },
            width: 96,
            height: 96,
            borderRadius: "50%",
            bgcolor: "secondary.main",
            color: "common.white",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: `0 12px 32px ${theme.palette.secondary.main}55`,
          }}
        >
          <CheckIcon sx={{ fontSize: 40 }} />
        </Box>
      </Paper>
    </Dialog>
  );
}
