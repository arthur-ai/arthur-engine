import { queryOptions } from "@tanstack/react-query";

import { Api } from "@/lib/api";
import { MAX_PAGE_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getUsers } from "@/services/tracing";

export const getUsersQueryOptions = ({
  api,
  taskId,
}: {
  api: Api<unknown>;
  taskId: string;
}) =>
  queryOptions({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.listPaginated(0, MAX_PAGE_SIZE),
    queryFn: () =>
      getUsers(api, { taskId, page: 0, pageSize: MAX_PAGE_SIZE, filters: [] }),
  });
