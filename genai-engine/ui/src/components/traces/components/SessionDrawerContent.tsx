import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { Stack, Typography } from "@mui/material";
import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent } from "react";

import { getSessionTotals } from "../utils/sessions";

import { TraceRenderer } from "./session/TraceRenderer";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";
import { getSession } from "@/services/tracing";
import { TokenCountTooltip } from "../data/common";

type Props = {
  id: string;
};

export const SessionDrawerContent = ({ id }: Props) => {
  const api = useApi()!;
  const queryClient = useQueryClient();

  const { data: session } = useSuspenseQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.sessions.byId(id),
    queryFn: () => getSession(api, { sessionId: id }),
  });

  const initOnTraces = useEffectEvent(() => {
    session.traces.forEach((trace) => {
      queryClient.setQueryData(queryKeys.traces.byId(trace.trace_id), trace);
    });
  });

  useEffect(() => {
    initOnTraces();
  }, [session.traces]);

  const totals = getSessionTotals(session);

  return (
    <Stack spacing={0} sx={{ height: "100%" }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 4,
          py: 2,
          backgroundColor: "grey.100",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="column" gap={1}>
          <Typography variant="body2" color="text.secondary">
            Session Details
          </Typography>
          <Typography variant="h5" color="text.primary" fontWeight="bold">
            {session.session_id}
          </Typography>
        </Stack>
      </Stack>

      <Stack gap={2} sx={{ p: 4 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <TokenCountTooltip
            prompt={totals[SemanticConventions.LLM_TOKEN_COUNT_PROMPT]}
            completion={totals[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION]}
            total={totals[SemanticConventions.LLM_TOKEN_COUNT_TOTAL]}
          />
        </Stack>
        <Typography variant="body1" color="text.primary" sx={{ my: 0 }}>
          <strong>{session.count} trace(s)</strong> in this session
        </Typography>
        {session.traces.map((trace) => (
          <TraceRenderer key={trace.trace_id} trace={trace} />
        ))}
      </Stack>
    </Stack>
  );
};
