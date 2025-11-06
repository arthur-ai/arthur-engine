import { useEffect, useEffectEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";

import { LEVELS } from "../constants";
import { type HistoryStore, type Level, type TargetBase, useTracesHistoryStore } from "../stores/history.store";

type Opts = {
  onLevelChange: (level: Level) => void;
};

export const useSyncUrlState = ({ onLevelChange }: Opts) => {
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

    onLevelChange(target);

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
};
