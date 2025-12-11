import { useQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent } from "react";

import { usePromptPlaygroundStore } from "../stores/playground.store";
import apiToFrontendPrompt from "../utils/apiToFrontendPrompt";

import { useApi } from "@/hooks/useApi";
import { SpanWithMetricsResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { getSpan } from "@/services/tracing";

type Opts = {
  spanId: string;
  enabled: boolean;
};

export const useSyncSpanData = ({ spanId, enabled }: Opts) => {
  const api = useApi()!;

  const actions = usePromptPlaygroundStore((state) => state.actions);
  const prompts = usePromptPlaygroundStore((state) => state.prompts);

  const span = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.spans.byId(spanId!),
    queryFn: () => getSpan(api, { spanId: spanId! }),
    enabled,
  });

  const handleSpanLoaded = useEffectEvent((data: SpanWithMetricsResponse) => {
    const spanPrompt = apiToFrontendPrompt(data);

    if (prompts.length > 0) {
      actions.updatePrompt(prompts[0].id, spanPrompt);
    } else {
      actions.addPrompt(spanPrompt);
    }
  });

  useEffect(() => {
    if (!span.data || !enabled) return;

    handleSpanLoaded(span.data);
  }, [span.data, enabled]);

  return {
    isLoading: span.isLoading,
  };
};
