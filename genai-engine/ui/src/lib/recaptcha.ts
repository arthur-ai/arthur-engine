/**
 * reCAPTCHA Enterprise (score-based / invisible) helpers.
 *
 * The Enterprise script is loaded lazily the first time a token is requested
 * (or via {@link preloadRecaptcha} on a likely-to-submit screen). When no site
 * key is configured, every entry point becomes a no-op so local/dev builds and
 * environments without reCAPTCHA keep working unchanged.
 */

const SITE_KEY = import.meta.env.VITE_RECAPTCHA_ENTERPRISE_SITE_KEY as string | undefined;
const SCRIPT_ID = "recaptcha-enterprise";
const BADGE_STYLE_ID = "recaptcha-badge-style";
const BADGE_VISIBLE_CLASS = "recaptcha-badge-visible";

interface GrecaptchaEnterprise {
  enterprise: {
    ready: (cb: () => void) => void;
    execute: (siteKey: string, options: { action: string }) => Promise<string>;
  };
}

declare global {
  interface Window {
    grecaptcha?: GrecaptchaEnterprise;
  }
}

let loadPromise: Promise<void> | null = null;

/** True when a reCAPTCHA Enterprise site key is configured at build time. */
export function isRecaptchaEnabled(): boolean {
  return Boolean(SITE_KEY);
}

/**
 * Injects (once) a stylesheet that keeps the floating reCAPTCHA badge hidden by
 * default and only reveals it while `<html>` carries {@link BADGE_VISIBLE_CLASS}.
 * Driving visibility through a root class (rather than the badge node itself)
 * survives the badge being created asynchronously after the script loads.
 */
function ensureBadgeStyle(): void {
  if (typeof document === "undefined" || document.getElementById(BADGE_STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = BADGE_STYLE_ID;
  style.textContent = `
    .grecaptcha-badge { visibility: hidden; opacity: 0; transition: opacity 0.2s ease; }
    html.${BADGE_VISIBLE_CLASS} .grecaptcha-badge { visibility: visible; opacity: 1; }
  `;
  document.head.appendChild(style);
}

/**
 * Shows or hides the floating reCAPTCHA badge. No-op when reCAPTCHA is not
 * configured. Hiding the badge on screens without a reCAPTCHA action is
 * permitted as long as the badge is shown where the action happens (the form).
 */
export function setRecaptchaBadgeVisible(visible: boolean): void {
  if (!SITE_KEY || typeof document === "undefined") return;
  ensureBadgeStyle();
  document.documentElement.classList.toggle(BADGE_VISIBLE_CLASS, visible);
}

function loadRecaptchaScript(siteKey: string): Promise<void> {
  if (loadPromise) return loadPromise;

  // Make sure the badge starts hidden before the script can render it.
  ensureBadgeStyle();

  loadPromise = new Promise<void>((resolve, reject) => {
    if (window.grecaptcha?.enterprise) {
      resolve();
      return;
    }

    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load reCAPTCHA Enterprise")));
      return;
    }

    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = `https://www.google.com/recaptcha/enterprise.js?render=${encodeURIComponent(siteKey)}`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loadPromise = null;
      reject(new Error("Failed to load reCAPTCHA Enterprise"));
    };
    document.head.appendChild(script);
  });

  return loadPromise;
}

/** Begin loading the reCAPTCHA script ahead of time. Safe to call repeatedly. */
export function preloadRecaptcha(): void {
  if (!SITE_KEY) return;
  void loadRecaptchaScript(SITE_KEY).catch(() => {
    /* swallowed; execution will retry/handle failure at submit time */
  });
}

/**
 * Returns a fresh reCAPTCHA Enterprise token for the given action, or `null`
 * when reCAPTCHA is not configured. Callers should send the token to the
 * backend, which performs the assessment.
 */
export async function executeRecaptcha(action: string): Promise<string | null> {
  if (!SITE_KEY) return null;

  await loadRecaptchaScript(SITE_KEY);
  const grecaptcha = window.grecaptcha;
  if (!grecaptcha?.enterprise) return null;

  await new Promise<void>((resolve) => grecaptcha.enterprise.ready(() => resolve()));
  return grecaptcha.enterprise.execute(SITE_KEY, { action });
}
