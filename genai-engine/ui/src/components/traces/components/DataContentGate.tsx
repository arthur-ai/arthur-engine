import { Box, CircularProgress, Typography } from "@mui/material";
import { useEffect } from "react";

import { useWelcomeStore } from "../stores/welcome.store";

import { TracesEmptyState } from "./TracesEmptyState";
import { TracesWelcomePage } from "./TracesWelcomePage";

import { useTask } from "@/hooks/useTask";

interface DataContentGateProps {
  welcomeDismissed: boolean;
  hasData: boolean;
  hasActiveFilters: boolean;
  isLoading?: boolean;
  dataType: "traces" | "spans" | "sessions" | "users";
  children: React.ReactNode;
}

export const DataContentGate = ({ welcomeDismissed, hasData, hasActiveFilters, isLoading, dataType, children }: DataContentGateProps) => {
  // Show onboarding only if user hasn't dismissed it AND has no data AND no active filters
  // This ensures users with existing traces skip onboarding even if they never saw it before
  const { task } = useTask();

  const store = useWelcomeStore(task?.id ?? "");

  const setDismissed = store((state) => state.setDismissed);

  useEffect(() => {
    if (welcomeDismissed) return;

    if (hasData) {
      setDismissed(true);
    }
  }, [hasData, setDismissed, welcomeDismissed]);

  if (!welcomeDismissed && !hasData && !hasActiveFilters) {
    return <TracesWelcomePage />;
  }

  // If we have data or active filters, show the children (which includes filters and conditionally the table)
  if (hasData || hasActiveFilters) {
    return (
      <>
        {children}
        {/* Show empty state message when filters are active but no data */}
        {!hasData && hasActiveFilters && (
          <TracesEmptyState title={`No ${dataType} found`}>
            <Typography variant="body1" color="text.secondary">
              Try adjusting your search query
            </Typography>
          </TracesEmptyState>
        )}
      </>
    );
  }

  // Show loading spinner while the initial fetch is in progress
  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  // Default empty state when no data and no filters
  return (
    <TracesEmptyState title={`No ${dataType} yet`}>
      <Typography variant="body1" color="text.secondary">
        {dataType.charAt(0).toUpperCase() + dataType.slice(1)} will appear here once your application starts sending data
      </Typography>
    </TracesEmptyState>
  );
};
