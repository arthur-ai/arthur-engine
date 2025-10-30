import { createStoreHook } from "@xstate/store/react";

export type Level = "trace" | "span" | "session" | "user";

export const useTracesStore = createStoreHook({
  context: {
    history: [] as { for: Level; id: string }[],
    selected: {
      span: "",
    },
  },
  emits: {
    changed: (_payload: { for: Level; id: string }) => {},
    closed: () => {},
  },
  on: {
    openDrawer: (context, event: { for: Level; id: string }, enqueue) => {
      const newHistory = [...context.history, { for: event.for, id: event.id }];

      enqueue.emit.changed({ for: event.for, id: event.id });

      return {
        ...context,
        history: newHistory,
      };
    },
    closeDrawer: (context, _: unknown, enqueue) => {
      enqueue.emit.closed();

      return {
        ...context,
        history: [],
        selected: {
          span: "",
        },
      };
    },
    popUntil: (context, event: { for: Level; id: string }, enqueue) => {
      const newHistory = [...context.history];

      // Find the index of the item that matches the criteria
      const matchIndex = newHistory.findIndex(
        (item) => item.for === event.for && item.id === event.id
      );

      // If found, keep everything up to and including the matched item
      const updatedHistory =
        matchIndex >= 0 ? newHistory.slice(0, matchIndex + 1) : newHistory;

      enqueue.emit.changed({ for: event.for, id: event.id });

      return {
        ...context,
        history: updatedHistory,
      };
    },
    setDrawer: (context, event: { for: Level; id: string }) => {
      return {
        ...context,
        history: [{ for: event.for, id: event.id }],
        selected: {
          ...context.selected,
        },
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
