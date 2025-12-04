import { capitalize } from "@mui/material";
import { QueryErrorResetBoundary } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";

import { TraceContentSkeleton } from "./TraceDrawerContent";

import { Drawer } from "@/components/common/Drawer";
import { ErrorFallback } from "@/components/common/ErrorFallback";
import { createTitle } from "@/utils/title";

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
  const [, select] = useSelection("span");
  const [current, setDrawerTarget] = useDrawerTarget();

  const handleClose = () => {
    setDrawerTarget({ id: null });
    select(null, { history: "replace" });
  };

  const Content = current?.id ? CONTENT_MAP[current?.target] : null;

  const shouldRender = !!Content;

  return (
    <>
      {shouldRender && <title>{createTitle(`${capitalize(current.target)} Details - ${current.id}`)}</title>}
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
          <AnimatePresence mode="popLayout">
            <motion.div
              key={current?.id}
              initial={{ opacity: 0, x: -64, filter: "blur(8px)" }}
              animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, x: 64, filter: "blur(8px)" }}
              transition={{ type: "spring", duration: 0.3 }}
              className="w-full flex-1 overflow-y-auto"
            >
              {Content && current && (
                <QueryErrorResetBoundary>
                  {({ reset }) => (
                    <ErrorBoundary key={current.id} onReset={reset} FallbackComponent={ErrorFallback}>
                      <Suspense fallback={<TraceContentSkeleton />}>
                        <Content id={current.id!} />
                      </Suspense>
                    </ErrorBoundary>
                  )}
                </QueryErrorResetBoundary>
              )}
            </motion.div>
          </AnimatePresence>
        </Drawer.Content>
      </Drawer>
    </>
  );
};
