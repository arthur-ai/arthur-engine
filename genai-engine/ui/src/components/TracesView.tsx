import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useState } from "react";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";

type Level = "trace" | "span" | "session";

export const TracesView: React.FC = () => {
  const [level, setLevel] = useState<Level>("trace");

  const handleLevelChange = (event: React.SyntheticEvent, newValue: Level) => {
    setLevel(newValue);
  };

  return (
    <>
      <Box
        sx={{
          maxHeight: "calc(100vh - 88px)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          p: 2,
          gap: 2,
        }}
      >
        <Tabs value={level} onChange={handleLevelChange}>
          <Tab value="trace" label="Trace Level" />
          <Tab value="span" label="Span Level" />
          <Tab value="session" label="Session Level" />
        </Tabs>

        <Activity mode={level === "trace" ? "visible" : "hidden"}>
          <TraceLevel />
        </Activity>
        <Activity mode={level === "span" ? "visible" : "hidden"}>
          <SpanLevel />
        </Activity>
        <Activity mode={level === "session" ? "visible" : "hidden"}>
          <SessionLevel />
        </Activity>
      </Box>

      <CommonDrawer />
    </>
  );
};
