export function waitForElement(selector: string, options: { timeoutMs?: number } = {}): Promise<Element> {
  const timeoutMs = options.timeoutMs ?? 5000;
  const existingElement = document.querySelector(selector);

  if (existingElement) {
    return Promise.resolve(existingElement);
  }

  return new Promise((resolve, reject) => {
    const observer = new MutationObserver(() => {
      const element = document.querySelector(selector);

      if (element) {
        clearTimeout(timeoutId);
        observer.disconnect();
        resolve(element);
      }
    });

    const timeoutId = window.setTimeout(() => {
      observer.disconnect();
      reject(new Error(`Tour target not found: ${selector}`));
    }, timeoutMs);

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  });
}
