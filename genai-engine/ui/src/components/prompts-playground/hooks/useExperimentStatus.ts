import { useQuery } from "@tanstack/react-query";
import { useSnackbar } from "notistack";

import { useExperimentStore } from "../stores/experiment.store";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

const REFRESH_INTERVAL = 2_000;

type Options = {
  /**
   * The interval in milliseconds to poll the experiment status.
   * @default 2000 milliseconds
   */
  interval?: number;
  onCompleted?: () => void;
};

export const useExperimentStatus = (
  { interval, onCompleted }: Options = {
    interval: REFRESH_INTERVAL,
  }
) => {
  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();

  const runningExperimentId = useExperimentStore((state) => state.runningExperimentId);

  useQuery({
    enabled: !!runningExperimentId,
    queryKey: [...queryKeys.promptExperiments.get(runningExperimentId!), "polling"],
    queryFn: async () => {
      try {
        const { data } = await api.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(runningExperimentId!);

        if (data.status === "completed") {
          onCompleted?.();
        } else {
          enqueueSnackbar("Experiment running with status: " + data.status, { variant: "info" });
        }

        return data;
      } catch (error) {
        console.error("Failed to get experiment:", error);
        enqueueSnackbar("Failed to get experiment", { variant: "error" });
        return null;
      }
    },
    refetchInterval: interval,
  });
};
