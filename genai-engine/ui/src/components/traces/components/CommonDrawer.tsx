import { Box, Breadcrumbs, Button } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { Drawer } from "vaul";

import { Level, useTracesStore } from "../store";

import { TraceContentSkeleton } from "./TraceDrawerContent";

const CONTENT_MAP = {
  trace: lazy(() =>
    import("./TraceDrawerContent").then((module) => ({
      default: module.TraceDrawerContent,
    }))
  ),
  span: lazy(() =>
    import("./SpanDrawerContent").then((module) => ({
      default: module.SpanDrawerContent,
    }))
  ),
  session: null,
  user: null,
};

export const CommonDrawer = () => {
  const [history, store] = useTracesStore((state) => state.context.history);
  const latestEntry = history.at(-1);

  const handleClose = () => {
    store.send({
      type: "closeDrawer",
    });
  };

  const handleBreadcrumbNavigation = (data: { for: Level; id: string }) => {
    store.send({
      type: "popUntil",
      ...data,
    });
  };

  const Content = latestEntry?.for ? CONTENT_MAP[latestEntry?.for] : null;

  const shouldRender = !!Content;

  return (
    <Drawer.Root
      open={shouldRender}
      onOpenChange={handleClose}
      direction="right"
    >
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
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Breadcrumbs
            aria-label="Drawer history"
            sx={{
              px: 4,
              py: 1,
              backgroundColor: "grey.300",
            }}
          >
            {history.slice(0, history.length - 1).map((entry) => (
              <Button
                key={entry.id}
                variant="text"
                onClick={() => handleBreadcrumbNavigation(entry)}
              >
                {entry.for} ({entry.id})
              </Button>
            ))}
            <Button disabled>{latestEntry?.for}</Button>
          </Breadcrumbs>
          <AnimatePresence mode="popLayout">
            <motion.div
              key={latestEntry?.id}
              initial={{ opacity: 0, x: -64, filter: "blur(8px)" }}
              animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, x: 64, filter: "blur(8px)" }}
              transition={{ type: "spring", duration: 0.3 }}
              className="w-full flex-1 overflow-y-auto"
            >
              {Content && latestEntry && (
                <ErrorBoundary
                  key={latestEntry.id}
                  fallback={<div>Something went wrong</div>}
                >
                  <Suspense fallback={<TraceContentSkeleton />}>
                    <Content id={latestEntry?.id} />
                  </Suspense>
                </ErrorBoundary>
              )}
            </motion.div>
          </AnimatePresence>
        </Box>
      </Drawer.Portal>
    </Drawer.Root>
  );
};
