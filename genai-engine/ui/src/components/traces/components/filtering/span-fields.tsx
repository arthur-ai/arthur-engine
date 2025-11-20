import { useQuery } from "@tanstack/react-query";

import { useFilterStore } from "../../stores/filter.store";

import { createDynamicEnumField, createPrimitiveField, Field } from "./fields";
import { TRACE_FIELDS } from "./trace-fields";
import { EnumOperators } from "./types";

import { Api } from "@/lib/api";
import { MAX_PAGE_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSpans, getUsers } from "@/services/tracing";

export const SPAN_FIELDS = [
  ...TRACE_FIELDS,
  createDynamicEnumField<{ taskId: string; api: Api<unknown> }, "span_ids">({
    name: "span_ids",
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
        queryKey: queryKeys.spans.listPaginated(params),
        queryFn: () => getFilteredSpans(api, params),
        select: (data) => data.spans.map((span) => span.span_id),
      });

      return { data: data ?? [], loading: isLoading };
    },
    getTriggerClassName: () => "font-mono",
    renderValue: (value) => {
      if (value.length === 0) return "Select span IDs...";

      const firstValue = value[0];
      const additionalValues = value.length > 1 ? ` (+${value.length - 1} more)` : "";

      return firstValue + additionalValues;
    },
  }),
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
  createPrimitiveField({
    name: "span_name",
    type: "text",
    operators: [EnumOperators.EQUALS],
  }),
] satisfies Field[];
