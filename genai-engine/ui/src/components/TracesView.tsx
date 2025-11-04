import { FormControl, InputLabel, MenuItem, Select, Stack } from "@mui/material";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useState } from "react";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
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

          <FormControl size="small" sx={{ ml: "auto" }}>
            <InputLabel id="time-range-label">Time range</InputLabel>
            <Select
              labelId="time-range-label"
              label="Time range"
              size="small"
              value={timeRange}
              onChange={(event) => setTimeRange(event.target.value as TimeRange)}
            >
              <MenuItem value={TIME_RANGES["5 minutes"]}>Past 5 minutes</MenuItem>
              <MenuItem value={TIME_RANGES["30 minutes"]}>Past 30 minutes</MenuItem>
              <MenuItem value={TIME_RANGES["1 day"]}>Past 1 day</MenuItem>
              <MenuItem value={TIME_RANGES["1 week"]}>Past 1 week</MenuItem>
              <MenuItem value={TIME_RANGES["1 month"]}>Past 1 month</MenuItem>
              <MenuItem value={TIME_RANGES["3 months"]}>Past 3 months</MenuItem>
              <MenuItem value={TIME_RANGES["1 year"]}>Past 1 year</MenuItem>
              <MenuItem value={TIME_RANGES["all time"]}>All time</MenuItem>
            </Select>
          </FormControl>
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
