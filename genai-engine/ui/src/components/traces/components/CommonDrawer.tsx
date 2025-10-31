import { Breadcrumbs, Button, IconButton, Stack } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

import {
  HistoryEntry,
  TargetBase,
  useTracesHistoryStore,
} from "../stores/history.store";

import { TraceContentSkeleton } from "./TraceDrawerContent";

import CloseIcon from "@mui/icons-material/Close";
import { Drawer } from "@/components/common/Drawer";
import { ErrorFallback } from "@/components/common/ErrorFallback";
import { useSelectionStore } from "../stores/selection.store";
import { QueryErrorResetBoundary } from "@tanstack/react-query";

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
  session: lazy(() =>
    import("./SessionDrawerContent").then((module) => ({
      default: module.SessionDrawerContent,
    }))
  ),
  user: lazy(() =>
    import("./UserDrawerContent").then((module) => ({
      default: module.UserDrawerContent,
    }))
  ),
};

export const CommonDrawer = () => {
  const current = useTracesHistoryStore((state) => state.current());
  const history = useTracesHistoryStore((state) => state.entries);
  const reset = useTracesHistoryStore((state) => state.reset);
  const popUntil = useTracesHistoryStore((state) => state.popUntil);
  const resetSelection = useSelectionStore((state) => state.reset);

  const handleClose = () => {
    reset();
    resetSelection();
  };

  const handleBreadcrumbNavigation = (entry: HistoryEntry<TargetBase>) => {
    popUntil(entry);
  };

  const Content = current?.target.type
    ? CONTENT_MAP[current?.target.type]
    : null;

  const shouldRender = !!Content;

  return (
    <Drawer open={shouldRender} onClose={handleClose}>
      <Drawer.Content
        slotProps={{
          paper: {
            sx: {
              width: "90%",
            },
          },
        }}
      >
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{
            px: 4,
            py: 1,
            backgroundColor: "grey.300",
          }}
        >
          <Breadcrumbs aria-label="Drawer history">
            {history.slice(0, history.length - 1).map((entry) => (
              <Button
                key={entry.ts}
                variant="text"
                onClick={() => handleBreadcrumbNavigation(entry)}
              >
                {entry.target.type} ({entry.target.id})
              </Button>
            ))}
            <Button disabled>{current?.target.type}</Button>
          </Breadcrumbs>
          <IconButton onClick={handleClose}>
            <CloseIcon />
          </IconButton>
        </Stack>
        <AnimatePresence mode="popLayout">
          <motion.div
            key={current?.key}
            initial={{ opacity: 0, x: -64, filter: "blur(8px)" }}
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, x: 64, filter: "blur(8px)" }}
            transition={{ type: "spring", duration: 0.3 }}
            className="w-full flex-1 overflow-y-auto"
          >
            {Content && current && (
              <QueryErrorResetBoundary>
                {({ reset }) => (
                  <ErrorBoundary
                    key={current.key}
                    onReset={reset}
                    FallbackComponent={ErrorFallback}
                  >
                    <Suspense fallback={<TraceContentSkeleton />}>
                      <Content id={current.target.id.toString()} />
                    </Suspense>
                  </ErrorBoundary>
                )}
              </QueryErrorResetBoundary>
            )}
          </motion.div>
        </AnimatePresence>
      </Drawer.Content>
    </Drawer>
  );
};
