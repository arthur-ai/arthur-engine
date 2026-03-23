import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent } from "react";

import { SessionDrawerBody } from "./drawer/SessionDrawerBody";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";
import { getSession } from "@/services/tracing";

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.traces]);

  return <SessionDrawerBody session={session} />;
};
