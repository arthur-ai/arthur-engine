import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { useState } from "react";
import { useParams } from "react-router-dom";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { TimeRangeSelect } from "./traces/components/TimeRangeSelect";
import { Level, TIME_RANGES, TimeRange } from "./traces/constants";
import { useDrawerTarget } from "./traces/hooks/useDrawerTarget";
import { useWelcomeStore } from "./traces/stores/welcome.store";
import { FilterStoreProvider } from "./traces/stores/filter.store";

export const TracesView: React.FC = () => {
  const [current, setDrawerTarget] = useDrawerTarget();
  const [timeRange, setTimeRange] = useState<TimeRange>(TIME_RANGES["1 month"]);
  const { id: taskId } = useParams<{ id: string }>();

  const welcomeStore = useWelcomeStore(taskId || "");
  const welcomeDismissed = welcomeStore((state) => state.dismissed);

  const level = (current?.target as Level) || "trace";

  const handleLevelChange = (newValue: Level) => {
    setDrawerTarget({ target: newValue });
  };

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "#f9fafb",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          p: 2,
          gap: 2,
          flex: 1,
          overflow: "hidden",
        }}
      >
        {welcomeDismissed && (
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ flexShrink: 0 }}>
            <Tabs value={level} onChange={(_, newValue) => handleLevelChange(newValue as Level)}>
              <Tab value="trace" label="Traces" />
              <Tab value="span" label="Spans" />
              <Tab value="session" label="Sessions" />
              <Tab value="user" label="Users" />
            </Tabs>

            <TimeRangeSelect value={timeRange} onValueChange={setTimeRange} />
          </Stack>
        )}

        <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {level === "trace" && (
            <FilterStoreProvider timeRange={timeRange}>
              <TraceLevel welcomeDismissed={welcomeDismissed} />
            </FilterStoreProvider>
          )}
          {level === "span" && (
            <FilterStoreProvider timeRange={timeRange}>
              <SpanLevel welcomeDismissed={welcomeDismissed} />
            </FilterStoreProvider>
          )}
          {level === "session" && (
            <FilterStoreProvider timeRange={timeRange}>
              <SessionLevel welcomeDismissed={welcomeDismissed} />
            </FilterStoreProvider>
          )}
          {level === "user" && (
            <FilterStoreProvider timeRange={timeRange}>
              <UserLevel welcomeDismissed={welcomeDismissed} />
            </FilterStoreProvider>
          )}
        </Box>
      </Box>

      <CommonDrawer />
    </Box>
  );
};
