import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Tooltip, Typography } from "@mui/material";
import { alpha, type Theme, useTheme } from "@mui/material/styles";
import { motion } from "framer-motion";
import { useState } from "react";
import useMeasure from "react-use-measure";

import { Annotation, isContinuousEvalAnnotation } from "./schema";
import { AnnotationsTable } from "./table";

import { CopyableChip } from "@/components/common";
import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";

type Props = {
  annotations: AgenticAnnotationResponse[];
  traceId: string;
  className?: string;
};

export const AnnotationCell = ({ annotations, traceId, className }: Props) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [ref, { width }] = useMeasure();

  const parsed = annotations
    .map((annotation) => {
      const parsed = Annotation.safeParse(annotation);
      if (!parsed.success) return;

      return parsed.data;
    })
    .filter((annotation): annotation is Annotation => Boolean(annotation));

  // Get annotation metrics
  const continuousEvalAnnotations = parsed.filter(isContinuousEvalAnnotation);
  const passedCount = parsed.filter((a) => a.annotation_score === 1).length;
  const failedCount = parsed.filter((a) => a.annotation_score === 0).length;
  const skippedCount = continuousEvalAnnotations.filter((a) => a.run_status === "skipped").length;
  const erroredCount = continuousEvalAnnotations.filter((a) => a.run_status === "error").length;

  const theme = useTheme();

  // Determine button color based on results
  const getButtonColor = (t: Theme) => {
    const totalResults = passedCount + failedCount + erroredCount + skippedCount;
    if (totalResults === 0) return t.palette.text.secondary;
    if (failedCount + erroredCount + skippedCount === 0) return t.palette.success.main;
    if (passedCount === 0) return t.palette.error.main;
    return t.palette.warning.main;
  };

  const buttonColor = getButtonColor(theme);

  const handleOpenModal = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    setModalOpen(true);
  };

  if (parsed.length === 0) return null;

  return (
    <>
      <Tooltip title={`Passed / Failed / Skipped / Errored (${parsed.length} total annotation${parsed.length !== 1 ? "s" : ""})`} arrow>
        <motion.button
          className={`group ${className ?? ""}`}
          style={{
            backgroundColor: alpha(buttonColor, 0.12),
            border: `1px solid ${alpha(buttonColor, 0.4)}`,
            color: buttonColor,
            borderRadius: 4,
            whiteSpace: "nowrap",
            overflow: "hidden",
            cursor: "pointer",
          }}
          animate={{ width: width || "auto" }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: "spring", bounce: 0, duration: 0.25 }}
          onClick={handleOpenModal}
        >
          <div ref={ref} className="overflow-visible w-min flex items-center">
            <Typography variant="caption" color="inherit" fontWeight={500} className="select-none leading-none" sx={{ mx: 1 }}>
              {passedCount} / {failedCount} / {skippedCount} / {erroredCount}
            </Typography>
            <Box
              className="group-hover:block group-focus-visible:block hidden"
              sx={{
                pl: 0.5,
                pr: 0.75,
                borderLeft: `1px solid ${alpha(buttonColor, 0.4)}`,
                backgroundColor: alpha(buttonColor, 0.1),
              }}
            >
              <OpenInFullIcon sx={{ fontSize: 12 }} />
            </Box>
          </div>
        </motion.button>
      </Tooltip>

      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="md" fullWidth onClick={(e) => e.stopPropagation()}>
        <DialogTitle className="flex items-center gap-2">
          <Typography variant="h6">Annotations for trace</Typography>
          <CopyableChip label={traceId} sx={{ fontFamily: "monospace" }} />
        </DialogTitle>
        <DialogContent dividers>
          <AnnotationsTable annotations={parsed} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModalOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
