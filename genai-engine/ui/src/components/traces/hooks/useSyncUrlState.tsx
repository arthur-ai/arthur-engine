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

    const newSearchParams = new URLSearchParams(searchParams);
    newSearchParams.delete("id");
    if (!current) return setSearchParams(newSearchParams);

    newSearchParams.set("id", current.target.id.toString());
    newSearchParams.set("target", current.target.type);

    setSearchParams(newSearchParams);
  });

  const onInitialLoad = useEffectEvent(() => {
    const target = (searchParams.get("target") ?? "trace") as Level;
    const id = searchParams.get("id") as string;

    if (!LEVELS.includes(target)) return;
    onLevelChange(target);

    if (!id) return;

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
