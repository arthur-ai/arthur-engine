import { Typography } from "@mui/material";

import { TracesEmptyState } from "./TracesEmptyState";
import { TracesWelcomePage } from "./TracesWelcomePage";

interface DataContentGateProps {
  welcomeDismissed: boolean;
  hasData: boolean;
  hasActiveFilters: boolean;
  dataType: "traces" | "spans" | "sessions" | "users";
  children: React.ReactNode;
}

export const DataContentGate = ({ welcomeDismissed, hasData, hasActiveFilters, dataType, children }: DataContentGateProps) => {
  if (!welcomeDismissed) {
    return <TracesWelcomePage />;
  }

  if (hasData) {
    return <>{children}</>;
  }

  if (hasActiveFilters) {
    return (
      <TracesEmptyState title={`No ${dataType} found`}>
        <Typography variant="body1" color="text.secondary">
          Try adjusting your search query
        </Typography>
      </TracesEmptyState>
    );
  }

  return (
    <TracesEmptyState title={`No ${dataType} yet`}>
      <Typography variant="body1" color="text.secondary">
        {dataType.charAt(0).toUpperCase() + dataType.slice(1)} will appear here once your application starts sending data
      </Typography>
    </TracesEmptyState>
  );
};
