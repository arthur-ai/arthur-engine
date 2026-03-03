import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { Level, type TimeRange } from "../constants";

import { TimeRangeSelect } from "./TimeRangeSelect";

type TracesViewLayoutProps = {
  level: Level;
  timeRange: TimeRange;
  onLevelChange: (level: Level) => void;
  onTimeRangeChange: (timeRange: TimeRange) => void;
  welcomeDismissed: boolean;
  children: React.ReactNode;
};

export const TracesViewLayout = ({ level, timeRange, onLevelChange, onTimeRangeChange, welcomeDismissed, children }: TracesViewLayoutProps) => {
  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.default",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              Traces
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Monitor and analyze inference traces
            </Typography>
          </Box>
          {welcomeDismissed && <TimeRangeSelect value={timeRange} onValueChange={onTimeRangeChange} />}
        </Stack>
      </Box>

      {welcomeDismissed && (
        <Tabs
          variant="fullWidth"
          value={level}
          onChange={(_, newValue) => onLevelChange(newValue as Level)}
          sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
        >
          <Tab value="trace" label="Traces" />
          <Tab value="span" label="Spans" />
          <Tab value="session" label="Sessions" />
          <Tab value="user" label="Users" />
        </Tabs>
      )}

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>{children}</Box>
    </Box>
  );
};
