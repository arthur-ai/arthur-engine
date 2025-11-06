import { useQuery } from "@tanstack/react-query";

import { useFilterStore } from "../../stores/filter.store";

import { createDynamicEnumField, Field } from "./fields";
import { EnumOperators } from "./types";

import { Api } from "@/lib/api";
import { MAX_PAGE_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getUsers } from "@/services/tracing";

export const SESSION_FIELDS = [
  createDynamicEnumField<{ taskId: string; api: Api<unknown> }, "user_ids">({
    type: "dynamic_enum",
    name: "user_ids",
    getTriggerClassName: () => "",
    renderValue: (value) => [value].flat().join(", "),
    operators: [EnumOperators.EQUALS, EnumOperators.IN],
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
  }),
] as const satisfies Field[];
