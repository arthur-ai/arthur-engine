import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { AnnotationCell } from "./AnnotationCell";
import { FeedbackPanel } from "./feedback/FeedbackPanel";

import { TOUR_IDS } from "@/features/task-tour";
import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";

type Props = {
  annotations: AgenticAnnotationResponse[];
  traceId: string;
  containerRef: React.RefObject<HTMLDivElement | null>;
};

/**
 * Combined eval-annotations + manual-feedback strip for the trace drawer header.
 * Uses `renderAnnotationBar` (not the split render props) so the row keeps the
 * layout users expect from pre-3.16.0 builds. Tour anchors live on the inner
 * wrappers — span-tree spotlighting uses `slotProps.spans` on the drawer body.
 */
export function TraceDrawerAnnotationBar({ annotations, traceId, containerRef }: Props) {
  const hasAnnotations = (annotations?.length ?? 0) > 0;

  return (
    <Stack direction="row" alignItems="center" spacing={2} sx={{ minHeight: 32 }}>
      <Box
        data-tour-id={TOUR_IDS.traceDrawerEvals}
        sx={{ display: "inline-flex", alignItems: "center", cursor: "default" }}
      >
        {hasAnnotations ? (
          <AnnotationCell annotations={annotations} traceId={traceId} />
        ) : (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ whiteSpace: "nowrap", cursor: "pointer" }}
            onClick={() => dispatchTourEvent(TASK_TOUR_EVENTS.annotationsReviewed)}
          >
            No eval annotations on this trace yet
          </Typography>
        )}
      </Box>
      <Box
        data-tour-id={TOUR_IDS.traceDrawerFeedback}
        sx={{ display: "inline-flex", alignItems: "center", ml: "auto" }}
      >
        <FeedbackPanel containerRef={containerRef} annotations={annotations} traceId={traceId} />
      </Box>
    </Stack>
  );
}
