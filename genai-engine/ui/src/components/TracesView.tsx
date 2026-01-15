import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { parseAsStringLiteral, useQueryState } from "nuqs";
import React, { Activity } from "react";
import { useParams } from "react-router-dom";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { TimeRangeSelect } from "./traces/components/TimeRangeSelect";
import { Level, LEVELS, TIME_RANGES } from "./traces/constants";
import { FilterStoreProvider } from "./traces/stores/filter.store";
import { useWelcomeStore } from "./traces/stores/welcome.store";

const TIME_RANGE_VALUES = Object.values(TIME_RANGES);

export const TracesView: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();

  const [level, setLevel] = useQueryState("level", parseAsStringLiteral(LEVELS).withDefault("trace"));
  const [timeRange, setTimeRange] = useQueryState("timeRange", parseAsStringLiteral(TIME_RANGE_VALUES).withDefault(TIME_RANGES["1 month"]));

  const welcomeStore = useWelcomeStore(taskId || "");
  const welcomeDismissed = welcomeStore((state) => state.dismissed);

  const handleLevelChange = (newValue: Level) => {
    setLevel(newValue);
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
      </Box>

      <CommonDrawer />
    </Box>
  );
};
