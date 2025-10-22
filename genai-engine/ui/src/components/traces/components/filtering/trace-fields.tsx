import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { useQuery } from "@tanstack/react-query";

import { createDynamicEnumField, createPrimitiveField, Field } from "./fields";
import { createFilterRow } from "./filters-row";
import { ComparisonOperators, EnumOperators } from "./types";
import { getEnumOptionLabel } from "./utils";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { getTracesQueryOptions } from "@/query-options/traces";

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
  createDynamicEnumField<void, "trace_ids">({
    name: "trace_ids",
    type: "dynamic_enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    itemToStringLabel: undefined,
    promise: function usePromise() {
      const api = useApi()!;
      const { task } = useTask();

      const query = useQuery({
        ...getTracesQueryOptions({ api, taskId: task?.id ?? "", filters: [] }),
        select: (data) => data.traces.map((trace) => trace.trace_id),
      });

      return query.promise;
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

export const { FiltersRow } = createFilterRow(TRACE_FIELDS, {
  trace_ids: undefined,
});
