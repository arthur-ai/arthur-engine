import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { TimeRangeSelect } from "./traces/components/TimeRangeSelect";
import { Level, TIME_RANGES, TimeRange } from "./traces/constants";
import { useDrawerTarget } from "./traces/hooks/useDrawerTarget";
import { FilterStoreProvider } from "./traces/stores/filter.store";

export const TracesView: React.FC = () => {
  const [current, setDrawerTarget] = useDrawerTarget();
  const [timeRange, setTimeRange] = useState<TimeRange>(TIME_RANGES["1 month"]);
  const { id: taskId } = useParams<{ id: string }>();

  // Check if welcome page has been dismissed
  const [welcomeDismissed, setWelcomeDismissed] = useState(() => {
    const STORAGE_KEY = `traces-welcome-steps-${taskId}`;
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Only show tabs if explicitly dismissed (user clicked "View Traces")
        return parsed.dismissed === true;
      } catch {
        return false; // On error, default to hiding tabs
      }
    }
    // No localStorage - new task, default to hiding tabs (show onboarding if no data)
    return false;
  });

  // Listen for changes to localStorage to update welcome dismissed state
  useEffect(() => {
    const handleStorageChange = () => {
      const STORAGE_KEY = `traces-welcome-steps-${taskId}`;
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          // Only show tabs if explicitly dismissed
          setWelcomeDismissed(parsed.dismissed === true);
        } catch {
          // ignore
        }
      }
    };

    // Listen for custom event for immediate updates
    const handleWelcomeUpdated = (event: CustomEvent) => {
      if (event.detail.taskId === taskId) {
        setWelcomeDismissed(event.detail.stepStatus.dismissed === true);
      }
    };

    window.addEventListener("traces-welcome-updated", handleWelcomeUpdated as EventListener);

    // Poll localStorage for changes as fallback (since localStorage events don't fire in same tab)
    const interval = setInterval(handleStorageChange, 500);

    return () => {
      window.removeEventListener("traces-welcome-updated", handleWelcomeUpdated as EventListener);
      clearInterval(interval);
    };
  }, [taskId]);

  const level = (current?.target as Level) ?? "trace";

  const handleLevelChange = (newValue: Level) => {
    setDrawerTarget({ target: newValue });
  };

  return (
    <>
      <Box
        sx={{
          height: "calc(100vh - 88px)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          p: 2,
          gap: 2,
        }}
      >
        {welcomeDismissed && (
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Tabs value={level} onChange={(_, newValue) => handleLevelChange(newValue as Level)}>
              <Tab value="trace" label="Traces" />
              <Tab value="span" label="Spans" />
              <Tab value="session" label="Sessions" />
              <Tab value="user" label="Users" />
            </Tabs>

            <TimeRangeSelect value={timeRange} onValueChange={setTimeRange} />
          </Stack>
        )}

        <Activity mode={level === "trace" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <TraceLevel welcomeDismissed={welcomeDismissed} />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "span" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <SpanLevel welcomeDismissed={welcomeDismissed} />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "session" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <SessionLevel welcomeDismissed={welcomeDismissed} />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "user" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <UserLevel welcomeDismissed={welcomeDismissed} />
          </FilterStoreProvider>
        </Activity>
      </Box>

      <CommonDrawer />
    </>
  );
};
