import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { useState } from "react";
import useMeasure from "react-use-measure";
import z from "zod";

import { Annotation } from "./schema";
import { AnnotationsTable } from "./table";

import { CopyableChip } from "@/components/common";
import type { AgenticAnnotationMetadataResponse } from "@/lib/api-client/api-client";
import { cn } from "@/utils/cn";

type Props = {
  annotations: AgenticAnnotationMetadataResponse[];
  traceId: string;
  className?: string;
};

const Annotations = z.array(Annotation);

export const AnnotationCell = ({ annotations, traceId, className }: Props) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [ref, { width }] = useMeasure();

  const parsed = Annotations.safeParse(annotations);

  if (!parsed.success) {
    return null;
  }

  const handleOpenModal = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    setModalOpen(true);
  };

  return (
    <>
      <motion.button
        className={cn(
          "bg-[color-mix(in_oklab,var(--color)_20%,white)] border border-(--color)/50 text-(--color) rounded-md text-nowrap overflow-hidden cursor-pointer group",
          className
        )}
        style={{ "--color": "var(--color-green-700)" } as React.CSSProperties}
        animate={{ width: width || "auto" }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: "spring", bounce: 0, duration: 0.25 }}
        onClick={handleOpenModal}
      >
        <div ref={ref} className="overflow-visible w-min flex items-center">
          {/* <Icon sx={{ fontSize: 12, ml: 1 }} /> */}
          <Typography variant="caption" color="inherit" fontWeight={500} className="select-none leading-none" sx={{ mx: 1 }}>
            {parsed.data.length} annotation(s)
          </Typography>
          <Box className="border-l border-(--color)/50 bg-(--color)/10 group-hover:block group-focus-visible:block hidden" sx={{ pl: 0.5, pr: 0.75 }}>
            <OpenInFullIcon sx={{ fontSize: 12 }} />
          </Box>
        </div>
      </motion.button>

      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} maxWidth="md" fullWidth onClick={(e) => e.stopPropagation()}>
        <DialogTitle className="flex items-center gap-2">
          <Typography variant="h6">Annotations for trace</Typography>
          <CopyableChip label={traceId} sx={{ fontFamily: "monospace" }} />
        </DialogTitle>
        <DialogContent dividers>
          <AnnotationsTable annotations={parsed.data} />
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
