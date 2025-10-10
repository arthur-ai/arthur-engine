import Box from "@mui/material/Box";
import { Suspense } from "react";
import { Drawer } from "vaul";

import { useTracesStore } from "../store";

import { TraceContentSkeleton, TraceDrawerContent } from "./TraceDrawerContent";

import { useTask } from "@/hooks/useTask";

export const TraceDrawer = () => {
  const { task } = useTask();
  const [traceId, store] = useTracesStore(
    (state) => state.context.selectedTraceId
  );

  const handleClose = () => {
    store.send({
      type: "deselectTrace",
    });
  };

  return (
    <Drawer.Root open={!!traceId} onOpenChange={handleClose} direction="right">
      <Drawer.Portal>
        <Box
          component={Drawer.Overlay}
          sx={{
            backgroundColor: "oklch(0 0 360 / 0.5)",
            position: "fixed",
            inset: 0,
            zIndex: 10,
          }}
        />

        <Box
          component={Drawer.Content}
          sx={{
            backgroundColor: "background.paper",
            position: "fixed",
            insetBlock: 0,
            right: 0,
            zIndex: 11,
            width: "80%",
          }}
        >
          {!!traceId && task && (
            <Suspense fallback={<TraceContentSkeleton />}>
              <TraceDrawerContent task={task} />
            </Suspense>
          )}
        </Box>
      </Drawer.Portal>
    </Drawer.Root>
  );
};
