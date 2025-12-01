import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from "@mui/material";
import Modal from "@mui/material/Modal";
import { motion } from "framer-motion";
import { useState } from "react";
import useMeasure from "react-use-measure";

import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { CopyableChip } from "@/components/common";

type Props = {
  annotation: AgenticAnnotationResponse;
  traceId: string;
};

export const AnnotationCell = ({ annotation, traceId }: Props) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [ref, { width }] = useMeasure();

  const score = annotation.annotation_score === 0 ? "unhelpful" : "helpful";
  const color = score === "unhelpful" ? "var(--color-red-700)" : "var(--color-green-700)";

  const Icon = score === "unhelpful" ? ThumbDownIcon : ThumbUpIcon;
  const description = annotation.annotation_description;

  const handleOpenModal = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!description) {
      return;
    }

    setModalOpen(true);
  };

  return (
    <>
      <motion.button
        className="bg-[color-mix(in_oklab,var(--color)_20%,white)] border border-(--color)/50 text-(--color) rounded-md text-nowrap overflow-hidden cursor-pointer group"
        style={{ "--color": color } as React.CSSProperties}
        animate={{ width: width || "auto" }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: "spring", bounce: 0, duration: 0.25 }}
        onClick={handleOpenModal}
      >
        <div ref={ref} className="overflow-visible w-min flex items-center">
          <Icon sx={{ fontSize: 12, ml: 1 }} />
          <Typography variant="caption" color="inherit" fontWeight={500} className="select-none leading-none" sx={{ mx: 1 }}>
            {score === "unhelpful" ? "Unhelpful" : "Helpful"}
          </Typography>
          {description ? (
            <Box
              className="border-l border-(--color)/50 bg-(--color)/10 group-hover:block group-focus-visible:block hidden"
              sx={{ pl: 0.5, pr: 0.75 }}
            >
              <OpenInFullIcon sx={{ fontSize: 12 }} />
            </Box>
          ) : null}
        </div>
      </motion.button>

      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="md" fullWidth onClick={(e) => e.stopPropagation()}>
        <DialogTitle className="flex items-center gap-2">
          <Typography variant="h6">Annotation for trace</Typography>
          <CopyableChip label={traceId} sx={{ fontFamily: "monospace" }} />
        </DialogTitle>
        <DialogContent dividers>
          {annotation.annotation_description ? (
            <TextField label="Annotation Description" multiline maxRows={4} fullWidth value={annotation.annotation_description} disabled />
          ) : null}
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
