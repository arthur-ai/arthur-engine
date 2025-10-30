import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import React, { Activity, useEffect, useEffectEvent, useState } from "react";

import { useSearchParams } from "react-router-dom";
import { CommonDrawer } from "./traces/components/CommonDrawer";
import { FilterStoreProvider } from "./traces/components/filtering/stores/filter.store";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { useTracesStore } from "./traces/store";

type Level = "trace" | "span" | "session" | "user";

export const TracesView: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [, store] = useTracesStore(() => null);
  const [level, setLevel] = useState<Level>("trace");

  const handleLevelChange = (_event: React.SyntheticEvent, newValue: Level) => {
    setLevel(newValue);
  };

  const handleInitialLoad = useEffectEvent(() => {
    const sources = ["trace", "span", "session", "user"];
    const params = Object.fromEntries(
      sources.map((source) => [source, searchParams.get(source)])
    );

    const firstNonNullParam = Object.entries(params).find(
      ([_, value]) => value !== null
    );

    if (firstNonNullParam) {
      const [source, id] = firstNonNullParam;
      setLevel(source as Level);

      store.send({
        type: "setDrawer",
        for: source as Level,
        id: id as string,
      });
    }
  });

  useEffect(handleInitialLoad, []);

  const handleChanged = useEffectEvent(
    (payload: { for: Level; id: string }) => {
      setSearchParams(() => {
        const newParams = new URLSearchParams();

        newParams.set(payload.for, payload.id);

        return newParams;
      });
    }
  );

  const handleClosed = useEffectEvent(() => {
    setSearchParams(() => {
      const newParams = new URLSearchParams();
      return newParams;
    });
  });

  useEffect(() => {
    const subscriptions = [
      store.on("changed", handleChanged),
      store.on("closed", handleClosed),
    ];

    return () => {
      subscriptions.forEach((subscription) => subscription.unsubscribe());
    };
  }, []);

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
