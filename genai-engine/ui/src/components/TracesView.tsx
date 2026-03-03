import { parseAsStringLiteral, useQueryState } from "nuqs";
import React, { Activity, memo } from "react";
import { useParams } from "react-router-dom";

import { CommonDrawer } from "./traces/components/CommonDrawer";
import { SessionLevel } from "./traces/components/tables/SessionLevel";
import { SpanLevel } from "./traces/components/tables/SpanLevel";
import { TraceLevel } from "./traces/components/tables/TraceLevel";
import { UserLevel } from "./traces/components/tables/UserLevel";
import { Level, LEVELS, TIME_RANGES, TracesViewLayout } from "@arthur/shared-components";
import { FilterStoreProvider } from "./traces/stores/filter.store";
import { useWelcomeStore } from "./traces/stores/welcome.store";

import { EVENT_NAMES, track } from "@/services/amplitude";

const TIME_RANGE_VALUES = Object.values(TIME_RANGES);

type LevelPaneProps = {
  timeRange: (typeof TIME_RANGE_VALUES)[number];
  welcomeDismissed: boolean;
};

const TraceLevelPane = memo(({ timeRange, welcomeDismissed }: LevelPaneProps) => (
  <FilterStoreProvider timeRange={timeRange}>
    <TraceLevel welcomeDismissed={welcomeDismissed} />
  </FilterStoreProvider>
));

const SpanLevelPane = memo(({ timeRange, welcomeDismissed }: LevelPaneProps) => (
  <FilterStoreProvider timeRange={timeRange}>
    <SpanLevel welcomeDismissed={welcomeDismissed} />
  </FilterStoreProvider>
));

const SessionLevelPane = memo(({ timeRange, welcomeDismissed }: LevelPaneProps) => (
  <FilterStoreProvider timeRange={timeRange}>
    <SessionLevel welcomeDismissed={welcomeDismissed} />
  </FilterStoreProvider>
));

const UserLevelPane = memo(({ timeRange, welcomeDismissed }: LevelPaneProps) => (
  <FilterStoreProvider timeRange={timeRange}>
    <UserLevel welcomeDismissed={welcomeDismissed} />
  </FilterStoreProvider>
));

export const TracesView: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();

  const [level, setLevel] = useQueryState("level", parseAsStringLiteral(LEVELS).withDefault("trace"));
  const [timeRange, setTimeRange] = useQueryState("timeRange", parseAsStringLiteral(TIME_RANGE_VALUES).withDefault(TIME_RANGES["1 month"]));

  const welcomeStore = useWelcomeStore(taskId || "");
  const welcomeDismissed = welcomeStore((state) => state.dismissed);

  const handleLevelChange = (newValue: Level) => {
    if (newValue !== level) {
      track(EVENT_NAMES.TRACING_LEVEL_CHANGED, {
        task_id: taskId ?? "",
        from_level: level,
        to_level: newValue,
        time_range: timeRange,
      });
    }
    setLevel(newValue);
  };

  const handleTimeRangeChange = (newValue: (typeof TIME_RANGE_VALUES)[number]) => {
    if (newValue !== timeRange) {
      track(EVENT_NAMES.TRACING_TIME_RANGE_CHANGED, {
        task_id: taskId ?? "",
        level,
        from_time_range: timeRange,
        to_time_range: newValue,
      });
    }
    setTimeRange(newValue);
  };

  return (
    <>
      <TracesViewLayout
        level={level}
        timeRange={timeRange}
        onLevelChange={handleLevelChange}
        onTimeRangeChange={handleTimeRangeChange}
        welcomeDismissed={welcomeDismissed}
      >
        <Activity mode={level === "trace" ? "visible" : "hidden"}>
          <TraceLevelPane timeRange={timeRange} welcomeDismissed={welcomeDismissed} />
        </Activity>
        <Activity mode={level === "span" ? "visible" : "hidden"}>
          <SpanLevelPane timeRange={timeRange} welcomeDismissed={welcomeDismissed} />
        </Activity>
        <Activity mode={level === "session" ? "visible" : "hidden"}>
          <SessionLevelPane timeRange={timeRange} welcomeDismissed={welcomeDismissed} />
        </Activity>
        <Activity mode={level === "user" ? "visible" : "hidden"}>
          <UserLevelPane timeRange={timeRange} welcomeDismissed={welcomeDismissed} />
        </Activity>
      </TracesViewLayout>

      <CommonDrawer />
    </>
  );
};
