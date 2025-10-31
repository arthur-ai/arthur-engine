import { Breadcrumbs, Button, IconButton, Stack } from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

import { Level, useTracesStore } from "../store";

import { TraceContentSkeleton } from "./TraceDrawerContent";

import CloseIcon from "@mui/icons-material/Close";
import { Drawer } from "@/components/common/Drawer";

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
                key={entry.id}
                variant="text"
                onClick={() => handleBreadcrumbNavigation(entry)}
              >
                {entry.for} ({entry.id})
              </Button>
            ))}
            <Button disabled>{latestEntry?.for}</Button>
          </Breadcrumbs>
          <IconButton onClick={handleClose}>
            <CloseIcon />
          </IconButton>
        </Stack>
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
      </Drawer.Content>
    </Drawer>
  );
};
