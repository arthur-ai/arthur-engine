import {
  useMutation,
  UseMutationOptions,
  UseMutationResult,
  useQueryClient,
  InvalidateQueryFilters,
} from "@tanstack/react-query";

interface UseApiMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  onSuccess?: (data: TData, variables: TVariables) => void | Promise<void>;
  onError?: (error: Error, variables: TVariables) => void;
  invalidateQueries?: InvalidateQueryFilters[];
  mutationOptions?: Omit<
    UseMutationOptions<TData, Error, TVariables>,
    "mutationFn" | "onSuccess" | "onError"
  >;
}

export function useApiMutation<TData = unknown, TVariables = unknown>(
  options: UseApiMutationOptions<TData, TVariables>
): UseMutationResult<TData, Error, TVariables> {
  const queryClient = useQueryClient();

  return useMutation<TData, Error, TVariables>({
    mutationFn: options.mutationFn,
    onSuccess: async (data, variables) => {
      if (options.invalidateQueries) {
        await Promise.all(
          options.invalidateQueries.map((filter) =>
            queryClient.invalidateQueries(filter)
          )
        );
      }

      if (options.onSuccess) {
        await options.onSuccess(data, variables);
      }
    },
    onError: (error, variables) => {
      if (options.onError) {
        options.onError(error, variables);
      }
    },
    ...options.mutationOptions,
  });
}
