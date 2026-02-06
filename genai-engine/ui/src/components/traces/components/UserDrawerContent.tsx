import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";

import { TIME_RANGES, type TimeRange } from "../constants";

import { UserDrawerBody } from "./drawer/UserDrawerBody";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";
import { getUser } from "@/services/tracing";

type Props = {
  id: string;
};

export const UserDrawerContent = ({ id }: Props) => {
  const api = useApi()!;
  const { task } = useTask();

  const [timeRange, setTimeRange] = useState<TimeRange>(TIME_RANGES["1 month"]);

  const { data: user } = useSuspenseQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.byId(id),
    queryFn: () => getUser(api, { taskId: task?.id ?? "", userId: id }),
  });

  return <UserDrawerBody user={user} timeRange={timeRange} onTimeRangeChange={setTimeRange} taskId={task?.id ?? ""} />;
};
