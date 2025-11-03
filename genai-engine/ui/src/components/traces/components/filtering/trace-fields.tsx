import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { useQuery } from "@tanstack/react-query";

import { createDynamicEnumField, createPrimitiveField, Field } from "./fields";
import { ComparisonOperators, EnumOperators } from "./types";
import { getEnumOptionLabel } from "./utils";

import { Api } from "@/lib/api";
import { MAX_PAGE_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces } from "@/services/tracing";

export const TRACE_FIELDS = [
  createPrimitiveField({
    name: "span_types",
    type: "enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    options: Object.values(OpenInferenceSpanKind),
    itemToStringLabel: undefined,
  }),
  createPrimitiveField({
    name: "query_relevance",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: 1,
  }),
  createPrimitiveField({
    name: "response_relevance",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: 1,
  }),
  createPrimitiveField({
    name: "trace_duration",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: Infinity,
  }),
  createPrimitiveField({
    name: "tool_selection",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1, 2].map(String),
    itemToStringLabel: getEnumOptionLabel,
  }),
  createPrimitiveField({
    name: "tool_usage",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1, 2].map(String),
    itemToStringLabel: getEnumOptionLabel,
  }),
  createDynamicEnumField<{ taskId: string; api: Api<unknown> }, "trace_ids">({
    name: "trace_ids",
    type: "dynamic_enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    itemToStringLabel: undefined,
    useData: function useData({ taskId, api }) {
      const { data, isLoading } = useQuery({
        queryKey: queryKeys.traces.listPaginated([], 0, MAX_PAGE_SIZE),
        queryFn: () =>
          getFilteredTraces(api, {
            taskId,
            page: 0,
            pageSize: MAX_PAGE_SIZE,
            filters: [],
          }),
        select: (data) => data.traces.map((trace) => trace.trace_id),
      });

      return { data: data ?? [], loading: isLoading };
    },
    getTriggerClassName: () => "font-mono",
    renderValue: (value) => {
      if (value.length === 0) return "Select trace IDs...";

      const firstValue = value[0];
      const additionalValues =
        value.length > 1 ? ` (+${value.length - 1} more)` : "";

      return firstValue + additionalValues;
    },
  }),
] as const satisfies Field[];
