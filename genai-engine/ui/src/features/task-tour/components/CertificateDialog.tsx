import { downloadFile } from "@arthur/shared-components";
import { useToBlob } from "@hugocxl/react-to-image";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/Download";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import XIcon from "@mui/icons-material/X";
import { Box, Button, Dialog, IconButton, Paper, Stack, Typography, useTheme } from "@mui/material";
import { alpha } from "@mui/material/styles";

import { ArthurLogo } from "@/components/common/ArthurLogo";

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
  return new Date().toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

/**
 * Completion dialog shown on `tour:end{reason:"completed"}`. Mirrors the
 * final certificate-screen design but renders as a modal rather than a
 * dedicated route so it overlays whichever task page the user finishes on.
 */
export function CertificateDialog({ open, recipientName = "Alex Rivera", issuedOn = formatToday(), onClose }: CertificateDialogProps) {
  const theme = useTheme();
  const shareText = `I completed Arthur AI's Intro to Evals course with the Arthur Evals Engine.`;
  const shareUrl = "https://www.arthur.ai/";
  const linkedInShareHref = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
  const xShareHref = `https://x.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`;

  // Capture to a Blob (not a data-URL string): `downloadFile` writes a Blob's
  // bytes verbatim, but wraps a string as text — feeding it the data URL from
  // `useToPng` produced a "PNG" file containing the data-URI text, not pixels.
  const [, downloadPng, ref] = useToBlob<HTMLDivElement>({
    onSuccess: (blob) => {
      if (blob) {
        downloadFile(blob, "certificate.png", "image/png");
      }
    },
  });

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
          sx: {
            borderRadius: 0,
            overflow: "visible",
            position: "relative",
            bgcolor: "background.paper",
          },
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
        ref={ref}
        elevation={0}
        sx={{
          position: "relative",
          m: 2,
          minHeight: { xs: 520, md: 480 },
          px: { xs: 3, md: 6 },
          py: { xs: 5, md: 4 },
          textAlign: "center",
          border: 2,
          borderColor: "secondary.dark",
          borderRadius: 3,
          overflow: "hidden",
          backgroundImage: `linear-gradient(to bottom, #FBF2D9, #F8D9B6)`,
          color: "common.black",
        }}
      >
        <Typography
          id="task-tour-certificate-title"
          variant="h2"
          sx={{
            fontFamily: '"Georgia", "Times New Roman", serif',
            fontSize: { xs: 36, md: 48 },
            fontWeight: 700,
            lineHeight: 1.05,
            letterSpacing: -1,
          }}
        >
          Certificate of Achievement
        </Typography>
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Georgia", "Times New Roman", serif',
            fontSize: { xs: 18, md: 22 },
            fontWeight: 600,
            mt: 1.25,
          }}
        >
          Arthur AI · Intro to Evals
        </Typography>
        <Typography
          variant="caption"
          sx={{
            display: "block",

            letterSpacing: 6,
            textTransform: "uppercase",
            fontWeight: 700,
            fontSize: 10,
            mt: { xs: 4, md: 4.5 },
            mb: 1.75,
          }}
        >
          THIS IS TO CERTIFY THAT
        </Typography>
        <Typography
          variant="h2"
          sx={{
            fontFamily: '"Georgia", "Times New Roman", serif',
            fontWeight: 700,

            fontSize: { xs: 42, md: 52 },
            lineHeight: 1.05,
            letterSpacing: -1,
          }}
        >
          {recipientName}
        </Typography>
        <Typography variant="body2" sx={{ lineHeight: 1.55, maxWidth: 650, mx: "auto", mt: 3 }}>
          Has successfully completed the{" "}
          <Box component="span" sx={{ fontWeight: 700 }}>
            Intro to Evals
          </Box>{" "}
          course and used the{" "}
          <Box component="span" sx={{ fontWeight: 700 }}>
            Arthur Evals Engine
          </Box>{" "}
          to design, measure, and ship a production-grade AI agent.
        </Typography>

        <Stack
          direction="row"
          alignItems="flex-end"
          justifyContent="space-between"
          sx={{
            position: { xs: "static", md: "absolute" },
            left: { md: 54 },
            right: { md: 54 },
            bottom: { md: 22 },
            mt: { xs: 8, md: 0 },
            gap: 2,
          }}
        >
          <Box sx={{ width: 150, textAlign: "center" }}>
            <Box
              sx={{
                width: 64,
                height: 64,
                mx: "auto",
                mb: 1.25,
                borderRadius: "50%",
                border: 2,
                borderColor: "warning.dark",
                bgcolor: alpha(theme.palette.warning.main, 0.34),
                boxShadow: `inset 0 0 0 5px ${alpha(theme.palette.warning.light, 0.46)}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ArthurLogo width={22} height={22} aria-hidden="true" />
            </Box>
            <Box sx={{ borderTop: 1, borderColor: "common.black", pt: 0.75 }}>
              <Typography variant="caption" sx={{ fontSize: 10 }}>
                Arthur AI Instructors
              </Typography>
            </Box>
          </Box>

          <Stack direction="row" alignItems="center" spacing={0.75} sx={{ pb: 3 }}>
            <ArthurLogo width={26} height={26} aria-hidden="true" />
            <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.5, opacity: 0.6 }}>
              Arthur
            </Typography>
          </Stack>

          <Box sx={{ width: 150, textAlign: "center", pb: 0.25 }}>
            <Typography variant="caption" sx={{ display: "block", mb: 0.75, fontFamily: '"Georgia", serif' }}>
              {issuedOn}
            </Typography>
            <Box sx={{ borderTop: 1, borderColor: "common.black", pt: 0.75 }}>
              <Typography variant="caption" sx={{ fontSize: 10 }}>
                Date
              </Typography>
            </Box>
          </Box>
        </Stack>
      </Paper>

      <Stack direction="row" justifyContent="center" spacing={1} sx={{ px: 2, pb: 1.5, flexWrap: "wrap", rowGap: 1 }}>
        <Button size="small" variant="contained" color="secondary" startIcon={<DownloadIcon sx={{ fontSize: 16 }} />} onClick={downloadPng}>
          Download PNG
        </Button>
        <Button
          size="small"
          variant="outlined"
          color="inherit"
          href={linkedInShareHref}
          target="_blank"
          rel="noopener"
          startIcon={<LinkedInIcon sx={{ fontSize: 16 }} />}
        >
          Share to LinkedIn
        </Button>
        <Button
          size="small"
          variant="outlined"
          color="inherit"
          href={xShareHref}
          target="_blank"
          rel="noopener"
          startIcon={<XIcon sx={{ fontSize: 14 }} />}
        >
          Share to X
        </Button>
      </Stack>
    </Dialog>
  );
}
