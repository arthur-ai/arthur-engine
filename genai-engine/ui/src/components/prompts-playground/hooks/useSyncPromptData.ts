import { useQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent } from "react";

import { usePromptPlaygroundStore } from "../stores/playground.store";
import { toFrontendPrompt } from "../utils";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticPrompt } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  enabled: boolean;
  promptName: string;
  promptVersion: string;
};

export const useSyncPromptData = ({ enabled, promptName, promptVersion }: Opts) => {
  const api = useApi()!;
  const { task } = useTask();

  const actions = usePromptPlaygroundStore((state) => state.actions);

  const prompt = useQuery({
    queryKey: queryKeys.prompts.version(task!.id, promptName, promptVersion),
    queryFn: () => api.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(promptName, promptVersion, task!.id),
    enabled: !!enabled,
    select: (data) => data?.data,
  });

  const handlePromptLoaded = useEffectEvent((data: AgenticPrompt) => {
    const frontendPrompt = toFrontendPrompt(data);
    actions.addPrompt(frontendPrompt);
  });

  useEffect(() => {
    if (!prompt.data || !enabled) return;

    handlePromptLoaded(prompt.data);
  }, [prompt.data, enabled]);

  return {
    isLoading: prompt.isLoading,
  };
};
