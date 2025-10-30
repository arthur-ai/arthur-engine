import {
  useQuery,
  UseQueryOptions,
  UseQueryResult,
} from "@tanstack/react-query";

import { useApi } from "./useApi";

import { Api } from "@/lib/api-client/api-client";

type ApiMethods = keyof Api<unknown>["api"];

type MethodParameters<T extends ApiMethods> = Parameters<
  Api<unknown>["api"][T]
>;

type MethodReturnType<T extends ApiMethods> = ReturnType<
  Api<unknown>["api"][T]
> extends Promise<{ data: infer R }>
  ? R
  : never;

interface UseApiQueryParams<T extends ApiMethods> {
  method: T;
  args: MethodParameters<T>;
  enabled?: boolean;
  queryOptions?: Omit<
    UseQueryOptions<MethodReturnType<T>, Error>,
    "queryKey" | "queryFn" | "enabled"
  >;
}

export function useApiQuery<T extends ApiMethods>(
  params: UseApiQueryParams<T>
): UseQueryResult<MethodReturnType<T>, Error> {
  const api = useApi();
  const { method, args, enabled = true, queryOptions } = params;

  return useQuery<MethodReturnType<T>, Error>({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: [method, ...args],
    queryFn: async () => {
      if (!api) throw new Error("API client not initialized");

      const apiMethod = api.api[method] as (
        ...args: MethodParameters<T>
      ) => Promise<{ data: MethodReturnType<T> }>;

      const response = await apiMethod(...args);
      return response.data;
    },
    enabled: !!api && enabled,
    ...queryOptions,
  });
}
