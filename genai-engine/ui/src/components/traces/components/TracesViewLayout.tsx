import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { Activity } from "react";

import { TimeRangeSelect } from "./TimeRangeSelect";
import { Level, TIME_RANGES, type TimeRange } from "../constants";

const TIME_RANGE_VALUES = Object.values(TIME_RANGES);

type TracesViewLayoutProps = {
  level: Level;
  timeRange: TimeRange;
  onLevelChange: (level: Level) => void;
  onTimeRangeChange: (timeRange: TimeRange) => void;
  welcomeDismissed: boolean;
  children: React.ReactNode;
};

export const TracesViewLayout = ({
  level,
  timeRange,
  onLevelChange,
  onTimeRangeChange,
  welcomeDismissed,
  children,
}: TracesViewLayoutProps) => {
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
            <Tabs value={level} onChange={(_, newValue) => onLevelChange(newValue as Level)}>
              <Tab value="trace" label="Traces" />
              <Tab value="span" label="Spans" />
              <Tab value="session" label="Sessions" />
              <Tab value="user" label="Users" />
            </Tabs>

            <TimeRangeSelect value={timeRange} onValueChange={onTimeRangeChange} />
          </Stack>
        )}

        <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
};
