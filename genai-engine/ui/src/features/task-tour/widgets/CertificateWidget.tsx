import { useCallback, useState } from "react";

import { CertificateDialog } from "../components/CertificateDialog";
import { getStoredRecipientName } from "../recipientName";

import { useTourEvent } from "@/features/tour";

export interface CertificateWidgetProps {
  workspaceLabel?: string;
}

/**
 * Mounts the completion-certificate dialog on `tour:end{ reason: "completed" }`.
 * The state plugin is what flips the persisted status to `"completed"` on the
 * same event; this widget owns only the modal UI side-effect so it can be
 * dismissed independently of the underlying persistence record.
 */
export function CertificateWidget({ workspaceLabel }: CertificateWidgetProps) {
  const [open, setOpen] = useState(false);
  // Captured from localStorage when the tour completes — set by the onboarding
  // form on signup. Left undefined when absent so the dialog's default applies.
  const [recipientName, setRecipientName] = useState<string | undefined>(undefined);

  useTourEvent(
    "tour:end",
    useCallback((event) => {
      if (event.reason === "completed") {
        setRecipientName(getStoredRecipientName() ?? undefined);
        setOpen(true);
      }
    }, [])
  );

  const handleClose = useCallback(() => setOpen(false), []);

  return <CertificateDialog open={open} recipientName={recipientName} workspaceLabel={workspaceLabel} onClose={handleClose} />;
}
