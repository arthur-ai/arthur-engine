import { createStoreHook } from "@xstate/store/react";

export type Level = "trace" | "span" | "session";

export const useTracesStore = createStoreHook({
  context: {
    history: [] as { for: Level; id: string }[],
    selected: {
      span: "",
    },
  },
  on: {
    openDrawer: (context, event: { for: Level; id: string }) => {
      const newHistory = [...context.history, { for: event.for, id: event.id }];

      return {
        ...context,
        history: newHistory,
      };
    },
    closeDrawer: (context) => {
      return {
        ...context,
        history: [],
        selected: {
          span: "",
        },
      };
    },
    popUntil: (context, event: { for: Level; id: string }) => {
      const newHistory = [...context.history];

      // Find the index of the item that matches the criteria
      const matchIndex = newHistory.findIndex(
        (item) => item.for === event.for && item.id === event.id
      );

      // If found, keep everything up to and including the matched item
      const updatedHistory =
        matchIndex >= 0 ? newHistory.slice(0, matchIndex + 1) : newHistory;

      return {
        ...context,
        history: updatedHistory,
      };
    },
    selectSpan: (context, event: { id: string }) => {
      return {
        ...context,
        selected: {
          ...context.selected,
          span: event.id,
        },
      };
    },
  },
});

export const useTracesHistoryLatestEntry = () => {
  const [history, store] = useTracesStore((state) => state.context.history);

  return [history.at(-1) ?? null, store] as const;
};
