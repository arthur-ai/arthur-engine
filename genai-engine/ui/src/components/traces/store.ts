import { createStoreHook } from "@xstate/store/react";

export const useTracesStore = createStoreHook({
  context: {
    selectedTraceId: null as string | null,
    selectedSpanId: null as string | null,
  },
  on: {
    selectTrace: (context, event: { id: string }) => {
      return {
        ...context,
        selectedTraceId: event.id,
      };
    },
    deselectTrace: (context) => {
      return {
        ...context,
        selectedTraceId: null,
      };
    },
    selectSpan: (context, event: { id: string }) => {
      return {
        ...context,
        selectedSpanId: event.id,
      };
    },
    deselectSpan: (context) => {
      return {
        ...context,
        selectedSpanId: null,
      };
    },
  },
});
