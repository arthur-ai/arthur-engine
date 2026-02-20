import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Tooltip, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { useState } from "react";
import useMeasure from "react-use-measure";

import { Annotation, isContinuousEvalAnnotation } from "./schema";
import { AnnotationsTable } from "./table";

import { CopyableChip } from "@/components/common";
import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { cn } from "@/utils/cn";

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

  // Determine button color based on results
  const getButtonColor = () => {
    const totalResults = passedCount + failedCount + erroredCount + skippedCount;
    if (totalResults === 0) return "var(--color-gray-600)"; // No continuous eval results

    if (failedCount + erroredCount === 0 && passedCount === 0) {
      return "var(--color-gray-600)"; // All skipped
    } else if (failedCount + erroredCount === 0) {
      return "var(--color-green-700)"; // All passed
    } else if (passedCount === 0) {
      return "var(--color-red-700)"; // All failed or errored
    } else {
      return "var(--color-yellow-700)"; // Mixed results
    }
  };

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
          className={cn(
            "bg-[color-mix(in_oklab,var(--color)_20%,white)] border border-(--color)/50 text-(--color) rounded-md text-nowrap overflow-hidden cursor-pointer group",
            className
          )}
          style={{ "--color": getButtonColor() } as React.CSSProperties}
          animate={{ width: width || "auto" }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: "spring", bounce: 0, duration: 0.25 }}
          onClick={handleOpenModal}
        >
          <div ref={ref} className="overflow-visible w-min flex items-center">
            {/* <Icon sx={{ fontSize: 12, ml: 1 }} /> */}
            <Typography variant="caption" color="inherit" fontWeight={500} className="select-none leading-none" sx={{ mx: 1 }}>
              {passedCount} / {failedCount} / {skippedCount} / {erroredCount}
            </Typography>
            <Box
              className="border-l border-(--color)/50 bg-(--color)/10 group-hover:block group-focus-visible:block hidden"
              sx={{ pl: 0.5, pr: 0.75 }}
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
