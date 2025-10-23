import { useQuery } from "@tanstack/react-query";

import { createDynamicEnumField, Field } from "./fields";
import { EnumOperators } from "./types";

import { Api } from "@/lib/api";
import { getUsersQueryOptions } from "@/query-options/users";

export const SESSION_FIELDS = [
  createDynamicEnumField<{ taskId: string; api: Api<unknown> }, "users">({
    type: "dynamic_enum",
    name: "users",
    getTriggerClassName: () => "w-full",
    renderValue: (value) => [value].flat().join(", "),
    operators: [EnumOperators.IN],
    itemToStringLabel: undefined,
    promise: function usePromise({ taskId, api }) {
      return useQuery({
        ...getUsersQueryOptions({ api, taskId }),
        select: (data) => data.users.map((user) => user.user_id),
      }).promise;
    },
  }),
] as const satisfies Field[];
