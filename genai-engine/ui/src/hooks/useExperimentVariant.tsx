import { queryOptions, useQuery } from "@tanstack/react-query";

import { queryKeys } from "@/lib/queryKeys";
import { getExperimentVariant } from "@/services/amplitude-experiment";

export const experimentVariantQueryOptions = ({ experimentName }: { experimentName: string }) => {
  return queryOptions({
    queryKey: queryKeys.amplitude.experiments.variant(experimentName),
    queryFn: () => getExperimentVariant(experimentName),
  });
};

export const useExperimentVariant = (experimentName: string) => {
  return useQuery(experimentVariantQueryOptions({ experimentName }));
};
