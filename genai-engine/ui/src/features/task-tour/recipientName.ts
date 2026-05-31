/**
 * Persisted display name for the completion certificate.
 *
 * Written from the onboarding form on a successful signup and read back by the
 * {@link CertificateWidget} when the tour completes. It lives in localStorage
 * rather than React state so it survives the navigation between the public
 * onboarding page and the in-app tour. When nothing is stored the certificate
 * falls back to its own default recipient.
 */
const RECIPIENT_NAME_STORAGE_KEY = "task-tour:recipient-name";

/** Persist a recipient name. No-ops for empty/whitespace input so a blank value never clobbers a real one. */
export function storeRecipientName(name: string): void {
  const trimmed = name.trim();
  if (!trimmed || typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(RECIPIENT_NAME_STORAGE_KEY, trimmed);
  } catch {
    // Ignore quota / privacy-mode failures.
  }
}

/** Read the stored recipient name, or `null` when none is set. */
export function getStoredRecipientName(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const trimmed = window.localStorage.getItem(RECIPIENT_NAME_STORAGE_KEY)?.trim();
    return trimmed ? trimmed : null;
  } catch {
    return null;
  }
}
