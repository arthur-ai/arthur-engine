import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useState } from "react";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { FilterStoreProvider } from "./traces/components/filtering/stores/filter.store";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";

type Level = "trace" | "span" | "session" | "user";

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
          <Tab value="trace" label="Traces" />
          <Tab value="span" label="Spans" />
          <Tab value="session" label="Sessions" />
          <Tab value="user" label="Users" />
        </Tabs>

        <Activity mode={level === "trace" ? "visible" : "hidden"}>
          <FilterStoreProvider>
            <TraceLevel />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "span" ? "visible" : "hidden"}>
          <FilterStoreProvider>
            <SpanLevel />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "session" ? "visible" : "hidden"}>
          <FilterStoreProvider>
            <SessionLevel />
          </FilterStoreProvider>
        </Activity>
        <Activity mode={level === "user" ? "visible" : "hidden"}>
          <FilterStoreProvider>
            <UserLevel />
          </FilterStoreProvider>
        </Activity>
      </Box>

      <CommonDrawer />
    </>
  );
};
