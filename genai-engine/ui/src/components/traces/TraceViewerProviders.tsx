import { type CopyOutcome, TraceCopyFeedbackProvider, TraceDisplaySettingsProvider } from "@arthur/shared-components";
import { useSnackbar } from "notistack";
import { type ReactNode, useCallback, useMemo } from "react";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";

/** Hands the shared trace viewer the user's display settings and the app's toasts. */
export const TraceViewerProviders = ({ children }: { children: ReactNode }) => {
  const { defaultCurrency, timezone, use24Hour } = useDisplaySettings();
  const { enqueueSnackbar } = useSnackbar();

  const displaySettings = useMemo(() => ({ currency: defaultCurrency, timezone, use24Hour }), [defaultCurrency, timezone, use24Hour]);

  const handleCopy = useCallback(
    ({ copied, message }: CopyOutcome) => {
      enqueueSnackbar(message, { variant: copied ? "success" : "error" });
    },
    [enqueueSnackbar]
  );

  return (
    <TraceDisplaySettingsProvider value={displaySettings}>
      <TraceCopyFeedbackProvider onCopy={handleCopy}>{children}</TraceCopyFeedbackProvider>
    </TraceDisplaySettingsProvider>
  );
};
