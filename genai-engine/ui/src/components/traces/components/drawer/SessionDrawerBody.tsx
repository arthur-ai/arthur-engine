import { Stack, Typography } from "@mui/material";

import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { getSessionTotals } from "../../utils/sessions";
import { TraceRenderer } from "../session/TraceRenderer";

import { TraceResponse } from "@/lib/api";
import { SessionTracesResponse } from "@/lib/api-client/api-client";

type SessionDrawerBodyProps = {
  session: SessionTracesResponse;
};

export const SessionDrawerBody = ({ session }: SessionDrawerBodyProps) => {
  const { token, cost } = getSessionTotals(session);

  return (
    <Stack spacing={0} sx={{ height: "100%" }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 4,
          py: 2,
          backgroundColor: "action.hover",
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
        <Stack direction="row" alignItems="center" gap={2}>
          <TokenCountTooltip prompt={token.prompt} completion={token.completion} total={token.total} />
          <TokenCostTooltip prompt={cost.prompt} completion={cost.completion} total={cost.total} />
        </Stack>
        <Typography variant="body1" color="text.primary" sx={{ my: 0 }}>
          <strong>{session.count} trace(s)</strong> in this session
        </Typography>
        {session.traces.map((trace: TraceResponse) => (
          <TraceRenderer key={trace.trace_id} trace={trace} />
        ))}
      </Stack>
    </Stack>
  );
};
