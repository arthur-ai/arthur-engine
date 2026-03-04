import { CommonDrawer as SharedCommonDrawer } from "@arthur/shared-components";
import { capitalize } from "@mui/material";
import { lazy } from "react";

import { useDrawerTarget } from "../hooks/useDrawerTarget";
import { useSelection } from "../hooks/useSelection";

import { TraceContentSkeleton } from "./TraceDrawerContent";

import { EVENT_NAMES, track } from "@/services/amplitude";
import { createTitle } from "@/utils/title";

type DrawerTarget = "trace" | "span" | "session" | "user";

const CONTENT_MAP: Record<DrawerTarget, React.LazyExoticComponent<React.ComponentType<{ id: string }>>> = {
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
        return <Content id={contentId} />;
      }}
      title={current ? createTitle(`${capitalize(current.target)} Details - ${current.id}`) : undefined}
      skeleton={<TraceContentSkeleton />}
    />
  );
};
