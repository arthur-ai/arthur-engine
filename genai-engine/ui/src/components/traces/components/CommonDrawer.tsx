import { CommonDrawer as SharedCommonDrawer } from "@arthur/shared-components";
import { capitalize } from "@mui/material";
import { lazy } from "react";

import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";

import { TraceContentSkeleton } from "./TraceDrawerContent";

import { DATA_TOUR } from "@/components/onboarding/data-tour";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { createTitle } from "@/utils/title";

type DrawerTarget = "trace" | "span" | "session" | "user";

/**
 * Wraps a lazy import factory to handle stale chunk load failures.
 *
 * When the app is redeployed, Vite generates new content-hashed chunk filenames.
 * Users with the old page still open will try to fetch stale chunk URLs that no
 * longer exist, causing "Failed to fetch dynamically imported module" errors.
 * Reloading the page fetches the updated index.html and the new chunk URLs.
 */
const lazyWithChunkReload = <T extends React.ComponentType<{ id: string }>>(factory: () => Promise<{ default: T }>): React.LazyExoticComponent<T> => {
  return lazy(() =>
    factory().catch((err: unknown) => {
      if (err instanceof TypeError && err.message.toLowerCase().includes("failed to fetch")) {
        window.location.reload();
      }
      throw err;
    })
  );
};

const CONTENT_MAP: Record<DrawerTarget, React.LazyExoticComponent<React.ComponentType<{ id: string }>>> = {
  trace: lazyWithChunkReload(() =>
    import("./TraceDrawerContent").then((module) => ({
      default: module.TraceDrawerContent,
    }))
  ),
  span: lazyWithChunkReload(() =>
    import("./SpanDrawerContent").then((module) => ({
      default: module.SpanDrawerContent,
    }))
  ),
  session: lazyWithChunkReload(() =>
    import("./SessionDrawerContent").then((module) => ({
      default: module.SessionDrawerContent,
    }))
  ),
  user: lazyWithChunkReload(() =>
    import("./UserDrawerContent").then((module) => ({
      default: module.UserDrawerContent,
    }))
  ),
};

export const CommonDrawer = () => {
  const [, select] = useSelection("span");
  const [current, setDrawerTarget] = useDrawerTarget();

  const handleClose = () => {
    if (current?.id) {
      track(EVENT_NAMES.TRACING_DRAWER_CLOSED, {
        level: current.target,
        id: current.id,
      });
    }
    setDrawerTarget({ id: null });
    select(null, { history: "replace" });
  };

  const open = !!current?.id;
  const target = current?.target ?? null;
  const id = current?.id ?? null;

  return (
    <SharedCommonDrawer
      open={open}
      target={target}
      id={id}
      onClose={handleClose}
      renderContent={({ target, id: contentId }: { target: DrawerTarget; id: string }) => {
        const Content = CONTENT_MAP[target];
        if (!Content) {
          console.error(`Unknown drawer target: ${target}`);
          return null;
        }
        return (
          <div data-tour={DATA_TOUR.TRACE_DRAWER} style={{ height: "100%" }}>
            <Content id={contentId} />
          </div>
        );
      }}
      title={current ? createTitle(`${capitalize(current.target)} Details - ${current.id}`) : undefined}
      skeleton={<TraceContentSkeleton />}
    />
  );
};
