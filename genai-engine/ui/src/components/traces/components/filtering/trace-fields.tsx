import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { useQuery } from "@tanstack/react-query";

import { useFilterStore } from "../../stores/filter.store";

import { createDynamicEnumField, createPrimitiveField, Field } from "./fields";
import { ComparisonOperators, EnumOperators } from "./types";
import { getEnumOptionLabel } from "./utils";

import { Api } from "@/lib/api";
import { MAX_PAGE_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSessions, getFilteredTraces, getUsers } from "@/services/tracing";

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
      const timeRange = useFilterStore((state) => state.timeRange);

      const params = {
        taskId,
        page: 0,
        pageSize: MAX_PAGE_SIZE,
        filters: [],
        timeRange,
      };

      const { data, isLoading } = useQuery({
        queryKey: queryKeys.traces.listPaginated(params),
        queryFn: () => getFilteredTraces(api, params),
        select: (data) => data.traces.map((trace) => trace.trace_id),
      });

      return { data: data ?? [], loading: isLoading };
    },
    getTriggerClassName: () => "font-mono",
    renderValue: (value) => {
      if (value.length === 0) return "Select trace IDs...";

      const firstValue = value[0];
      const additionalValues = value.length > 1 ? ` (+${value.length - 1} more)` : "";

      return firstValue + additionalValues;
    },
  }),
  createPrimitiveField({
    name: "annotation_score",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1].map(String),
    itemToStringLabel: (option) => (option === "0" ? "Unhelpful" : "Helpful"),
  }),
  createDynamicEnumField<{ taskId: string; api: Api<unknown> }, "session_ids">({
    name: "session_ids",
    type: "dynamic_enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    itemToStringLabel: undefined,
    useData: function useData({ taskId, api }) {
      const timeRange = useFilterStore((state) => state.timeRange);

      const params = {
        taskId,
        page: 0,
        pageSize: MAX_PAGE_SIZE,
        filters: [],
        timeRange,
      };

      const { data, isLoading } = useQuery({
        queryKey: queryKeys.sessions.listPaginated(params),
        queryFn: () => getFilteredSessions(api, params),
        select: (data) => data.sessions.map((session) => session.session_id),
      });

      return { data: data ?? [], loading: isLoading };
    },
    getTriggerClassName: () => "font-mono",
    renderValue: (value) => {
      if (value.length === 0) return "Select session IDs...";

      const firstValue = value[0];
      const additionalValues = value.length > 1 ? ` (+${value.length - 1} more)` : "";

      return firstValue + additionalValues;
    },
  }),

  /*
    createDynamicEnumField creates a field definition for filter fields whose options are
    fetched at runtime, rather than being static. It defines enum fields where the options
    come from an API call, not a fixed list. Used for fields like:
      trace_ids — fetches available trace IDs
      session_ids — fetches available session IDs
      user_ids — fetches available user IDs
      span_ids — fetches available span IDs
   */
  createDynamicEnumField<{ taskId: string; api: Api<unknown> }, "user_ids">({
    name: "user_ids",
    type: "dynamic_enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    itemToStringLabel: undefined,
    useData: function useData({ taskId, api }) {
      const timeRange = useFilterStore((state) => state.timeRange);

      const params = {
        taskId,
        page: 0,
        pageSize: MAX_PAGE_SIZE,
        filters: [],
        timeRange,
      };

      const { data, isLoading } = useQuery({
        queryKey: queryKeys.users.listPaginated(params),
        queryFn: () => getUsers(api, params),
        select: (data) => data.users.map((user) => user.user_id),
      });

      return { data: data ?? [], loading: isLoading };
    },
    getTriggerClassName: () => "",
    renderValue: (value) => [value].flat().join(", "),
  }),
] as const satisfies Field[];
