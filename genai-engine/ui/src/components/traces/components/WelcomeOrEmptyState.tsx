import { Box, Typography } from "@mui/material";

import { TracesEmptyState } from "./TracesEmptyState";
import { TracesWelcomePage } from "./TracesWelcomePage";

interface WelcomeOrEmptyStateProps {
  hasActiveFilters: boolean;
  welcomeDismissed: boolean;
  dataType: "traces" | "spans" | "sessions" | "users";
}

export const WelcomeOrEmptyState = ({ hasActiveFilters, welcomeDismissed, dataType }: WelcomeOrEmptyStateProps) => {
  if (hasActiveFilters) {
    return (
      <TracesEmptyState title={`No ${dataType} found`}>
        <Typography variant="body1" color="text.secondary">
          Try adjusting your search query
        </Typography>
      </TracesEmptyState>
    );
  }

  if (welcomeDismissed) {
    return (
      <TracesEmptyState title={`No ${dataType} yet`}>
        <Typography variant="body1" color="text.secondary">
          {dataType.charAt(0).toUpperCase() + dataType.slice(1)} will appear here once your application starts sending data
        </Typography>
      </TracesEmptyState>
    );
  }

  return <TracesWelcomePage />;
};
