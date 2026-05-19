export const WAIT_FOR_TARGET_TIMEOUT_MS = 5000;

export const waitForSelectorInDom = (selector: string, timeoutMs: number = WAIT_FOR_TARGET_TIMEOUT_MS): Promise<boolean> => {
  return new Promise((resolve) => {
    if (document.querySelector(selector)) {
      resolve(true);
      return;
    }

    const cleanup = () => {
      observer.disconnect();
      window.clearTimeout(timer);
    };

    const observer = new MutationObserver(() => {
      if (document.querySelector(selector)) {
        cleanup();
        resolve(true);
      }
    });

    const timer = window.setTimeout(() => {
      cleanup();
      resolve(false);
    }, timeoutMs);

    observer.observe(document.body, { childList: true, subtree: true });
  });
};
