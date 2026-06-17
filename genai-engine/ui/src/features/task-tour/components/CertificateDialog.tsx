import { downloadFile } from "@arthur/shared-components";
import { useToBlob } from "@hugocxl/react-to-image";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/Download";
import LinkedInIcon from "@mui/icons-material/LinkedIn";
import XIcon from "@mui/icons-material/X";
import { Box, Button, Dialog, IconButton, Paper, Stack, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";

import { COURSE_NAME } from "../courseName";

import { ArthurSeal } from "./arthur-seal";

import { ArthurLogo } from "@/components/common/ArthurLogo";
import { track } from "@/services/analytics";

// Warm ink + parchment tones from the classic-diploma design. Kept as literals
// because they're fixed brand-artwork values, not themeable surface colors.
const INK = "#1A0016";
const INK_LINE = "rgba(26, 0, 22, 0.55)";
const EYEBROW = "#3A2A18";
const CITATION = "#2A1F18";

export interface CertificateDialogProps {
  open: boolean;
  /** Display name shown on the certificate. Falls back to a generic recipient. */
  recipientName?: string;
  /** Pre-formatted issue date. Defaults to today, rendered as `MMM D, YYYY`. */
  issuedOn?: string;
  onClose: () => void;
}

function formatToday(): string {
  return new Date().toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

async function uploadCertificate(blob: Blob): Promise<string | null> {
  try {
    const form = new FormData();
    form.append("file", blob, "certificate.png");
    const res = await fetch("/api/v2/demo/certificate", { method: "POST", body: form });
    if (!res.ok) return null;
    const data = (await res.json()) as { certificate_url: string };
    const path = data.certificate_url ?? null;
    if (!path) return null;
    return `${window.location.origin}${path}`;
  } catch {
    return null;
  }
}

/**
 * Completion dialog shown on `tour:end{reason:"completed"}`. Mirrors the
 * final certificate-screen design but renders as a modal rather than a
 * dedicated route so it overlays whichever task page the user finishes on.
 *
 * On open the certificate is captured and silently uploaded to the backend so
 * a stable public URL is available for social sharing. Download still works
 * even when the upload fails.
 */
export function CertificateDialog({ open, recipientName = "Alex Rivera", issuedOn = formatToday(), onClose }: CertificateDialogProps) {
  const [certificateUrl, setCertificateUrl] = useState<string | null>(null);
  // Holds the blob for the download button so we don't re-render to get it.
  const blobRef = useRef<Blob | null>(null);
  // Prevent triggering a second upload if the dialog is closed and reopened.
  const uploadedRef = useRef(false);
  // Set when the user clicks download before the capture has finished, so the
  // blob is downloaded as soon as it's ready rather than silently dropped.
  const pendingDownloadRef = useRef(false);

  const shareText = `I completed Arthur AI's ${COURSE_NAME} course with the Arthur Evals Engine.`;
  const shareUrl = certificateUrl ?? "https://www.arthur.ai/";
  const linkedInShareHref = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
  const xShareHref = `https://x.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`;

  const [, convertToBlob, ref] = useToBlob<HTMLDivElement>({
    onSuccess: async (blob) => {
      if (!blob) return;
      blobRef.current = blob;
      if (pendingDownloadRef.current) {
        pendingDownloadRef.current = false;
        downloadFile(blob, "certificate.png", "image/png");
      }
      if (!uploadedRef.current) {
        uploadedRef.current = true;
        const url = await uploadCertificate(blob);
        if (url) setCertificateUrl(url);
      }
    },
  });

  // Trigger capture shortly after the dialog opens so the DOM is rendered.
  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(convertToBlob, 150);
    return () => clearTimeout(timer);
    // convertToBlob is stable across renders; open is the only relevant dep.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const downloadPng = () => {
    if (blobRef.current) {
      downloadFile(blobRef.current, "certificate.png", "image/png");
    } else {
      pendingDownloadRef.current = true;
      void convertToBlob();
    }
  };

  // Both affordances advance to the CTA via `onClose`; the `method` records
  // which one the user used, surfacing whether the explicit "Continue" button
  // or the easy-to-miss corner "X" is what people reach for.
  const handleClose = (method: "continue" | "dismiss") => {
    track("onboarding/wizard_certificate_closed", { method, course: COURSE_NAME });
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={() => handleClose("dismiss")}
      maxWidth="md"
      fullWidth
      aria-labelledby="task-tour-certificate-title"
      slotProps={{
        paper: {
          elevation: 16,
          sx: {
            borderRadius: 0,
            overflow: "hidden",
            position: "relative",
            bgcolor: "background.paper",
            display: "flex",
            flexDirection: "column",
          },
        },
      }}
    >
      <IconButton
        size="small"
        onClick={() => handleClose("dismiss")}
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

      <Box sx={{ overflowY: "auto", flex: 1, minHeight: 0 }}>
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
            borderColor: INK,
            borderRadius: 3,
            overflow: "hidden",
            backgroundImage: `linear-gradient(180deg, #FBF2D9 0%, #F7D8B5 100%)`,
            color: INK,
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
              color: EYEBROW,
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
          <Typography variant="body2" sx={{ lineHeight: 1.55, maxWidth: 650, mx: "auto", mt: 3, color: CITATION }}>
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
              <Box sx={{ mb: 1, display: "flex", justifyContent: "center" }}>
                <ArthurSeal size={104} />
              </Box>
              <Box sx={{ borderTop: 1, borderColor: INK_LINE, pt: 0.75 }}>
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
              <Box sx={{ borderTop: 1, borderColor: INK_LINE, pt: 0.75 }}>
                <Typography variant="caption" sx={{ fontSize: 10 }}>
                  Date
                </Typography>
              </Box>
            </Box>
          </Stack>
        </Paper>
      </Box>

      <Stack direction="row" justifyContent="center" spacing={1} sx={{ px: 2, pb: 1.5, flexWrap: "wrap", rowGap: 1 }}>
        <Button
          size="small"
          variant="contained"
          color="secondary"
          startIcon={<DownloadIcon sx={{ fontSize: 16 }} />}
          onClick={() => {
            track("onboarding/wizard_certificate_download_clicked", { course: COURSE_NAME });
            downloadPng();
          }}
        >
          Download PNG
        </Button>
        <Button
          size="small"
          variant="outlined"
          color="inherit"
          href={linkedInShareHref}
          target="_blank"
          rel="noopener"
          onClick={() => track("onboarding/wizard_certificate_share_clicked", { destination: "linkedin", course: COURSE_NAME })}
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
          onClick={() => track("onboarding/wizard_certificate_share_clicked", { destination: "x", course: COURSE_NAME })}
          startIcon={<XIcon sx={{ fontSize: 14 }} />}
        >
          Share to X
        </Button>
        {/* Primary forward action. The corner close affordance is easy to miss
            against the parchment artwork, so give the flow an explicit next step;
            `onClose` advances the post-completion sequence to the CTA. */}
        <Button
          size="small"
          variant="contained"
          color="primary"
          endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
          onClick={() => handleClose("continue")}
        >
          Continue
        </Button>
      </Stack>
    </Dialog>
  );
}
