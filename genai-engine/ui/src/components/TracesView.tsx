import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useEffect, useEffectEvent, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { FilterStoreProvider } from "./traces/stores/filter.store";
import {
  HistoryStore,
  TargetBase,
  useTracesHistoryStore,
} from "./traces/stores/history.store";

const LEVELS = ["trace", "span", "session", "user"] as const;
type Level = (typeof LEVELS)[number];

export const TracesView: React.FC = () => {
  const [level, setLevel] = useState<Level>("trace");
  const reset = useTracesHistoryStore((state) => state.reset);
  const [searchParams, setSearchParams] = useSearchParams();

  const onHistoryChange = useEffectEvent((state: HistoryStore<TargetBase>) => {
    const current = state.current();

    const searchParams = new URLSearchParams();
    if (!current) return setSearchParams(searchParams);

    searchParams.set("target", current.target.type);
    searchParams.set("id", current.target.id.toString());

    setSearchParams(searchParams);
  });

  const onInitialLoad = useEffectEvent(() => {
    const target = searchParams.get("target") as Level;
    const id = searchParams.get("id") as string;

    if (!target || !id) return;
    if (!LEVELS.includes(target)) return;

    setLevel(target);
    reset([
      {
        key: uuidv4(),
        target: { type: target, id },
        ts: Date.now(),
      },
    ]);
  });

  useEffect(() => {
    return useTracesHistoryStore.subscribe(onHistoryChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(onInitialLoad, []);

  const handleLevelChange = (_event: React.SyntheticEvent, newValue: Level) => {
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
