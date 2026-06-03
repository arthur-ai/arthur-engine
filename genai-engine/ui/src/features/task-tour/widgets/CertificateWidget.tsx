import { useCallback, useState } from "react";

import { CertificateDialog, COURSE_NAME } from "../components/CertificateDialog";
import { CtaDialog } from "../components/cta-dialog";
import { getStoredRecipientName } from "../recipientName";

import { useTourEvent } from "@/features/tour";
import { EVENT_NAMES, track } from "@/services/amplitude";

/** Which post-completion dialog is currently showing, if any. */
type CompletionStage = "none" | "certificate" | "cta";

/**
 * Orchestrates the post-completion dialog sequence shown on
 * `tour:end{ reason: "completed" }`: first the achievement certificate, then a
 * call-to-action to book time with Arthur's CTO. Both are pure UI side-effects
 * of the same completion event, so a single widget owns the hand-off between
 * them. The state plugin is what flips the persisted status to `"completed"`;
 * this widget only drives the modals and can be dismissed independently.
 */
export function CertificateWidget() {
  const [stage, setStage] = useState<CompletionStage>("none");
  // Captured from localStorage when the tour completes — set by the onboarding
  // form on signup. Left undefined when absent so the dialog's default applies.
  const [recipientName, setRecipientName] = useState<string | undefined>(undefined);

  useTourEvent(
    "tour:end",
    useCallback((event) => {
      if (event.reason === "completed") {
        setRecipientName(getStoredRecipientName() ?? undefined);
        setStage("certificate");
        track(EVENT_NAMES.CERTIFICATE_VIEWED, { course: COURSE_NAME });
      }
    }, [])
  );

  // Closing the certificate advances to the CTA rather than ending the sequence.
  const handleCertificateClose = useCallback(() => setStage("cta"), []);
  const handleCtaDismiss = useCallback(() => setStage("none"), []);

  return (
    <>
      <CertificateDialog open={stage === "certificate"} recipientName={recipientName} onClose={handleCertificateClose} />
      <CtaDialog open={stage === "cta"} onDismiss={handleCtaDismiss} />
    </>
  );
}
