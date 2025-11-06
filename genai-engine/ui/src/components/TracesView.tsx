import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useState } from "react";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { TimeRangeSelect } from "./traces/components/TimeRangeSelect";
import { Level, TIME_RANGES, TimeRange } from "./traces/constants";
import { useSyncUrlState } from "./traces/hooks/useSyncUrlState";
import { FilterStoreProvider } from "./traces/stores/filter.store";

export const TracesView: React.FC = () => {
  const [level, setLevel] = useState<Level>("trace");
  const [timeRange, setTimeRange] = useState<TimeRange>(TIME_RANGES["1 month"]);

  const handleLevelChange = (_event: React.SyntheticEvent, newValue: Level) => {
    setLevel(newValue);
  };

  useSyncUrlState({ onLevelChange: setLevel });

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
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Tabs value={level} onChange={handleLevelChange}>
            <Tab value="trace" label="Traces" />
            <Tab value="span" label="Spans" />
            <Tab value="session" label="Sessions" />
            <Tab value="user" label="Users" />
          </Tabs>

          <TimeRangeSelect value={timeRange} onValueChange={setTimeRange} />
        </Stack>

        <Activity mode={level === "trace" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <TraceLevel />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "span" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <SpanLevel />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "session" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <SessionLevel />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "user" ? "visible" : "hidden"}>
          <FilterStoreProvider timeRange={timeRange}>
            <UserLevel />
          </FilterStoreProvider>
        </Activity>
      </Box>

      <CommonDrawer />
    </>
  );
};
