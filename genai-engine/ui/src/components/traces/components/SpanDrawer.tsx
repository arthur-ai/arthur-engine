import Box from "@mui/material/Box";
import { Suspense } from "react";
import { Drawer } from "vaul";

import { useTracesStore } from "../store";

import { SpanDrawerContent } from "./SpanDrawerContent";
import { TraceContentSkeleton } from "./TraceDrawerContent";

export const SpanDrawer = () => {
  const [spanId, store] = useTracesStore(
    (state) => state.context.selected.span
  );

  const handleClose = () => {
    store.send({
      type: "closeDrawer",
    });
  };

  return (
    <Drawer.Root open={!!spanId} onOpenChange={handleClose} direction="right">
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
          {!!spanId && (
            <Suspense fallback={<TraceContentSkeleton />}>
              <SpanDrawerContent />
            </Suspense>
          )}
        </Box>
      </Drawer.Portal>
    </Drawer.Root>
  );
};
