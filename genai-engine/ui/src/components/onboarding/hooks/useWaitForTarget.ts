import { useEffect, useState } from "react";

import { waitForSelectorInDom } from "../utils/waitForSelector";

export const useWaitForTarget = (selector: string | null, deps: ReadonlyArray<unknown> = []): boolean => {
  const [present, setPresent] = useState<boolean>(() => !!selector && !!document.querySelector(selector));

  useEffect(() => {
    if (!selector) {
      setPresent(false);
      return;
    }

    if (document.querySelector(selector)) {
      setPresent(true);
      return;
    }

    setPresent(false);
    let cancelled = false;
    waitForSelectorInDom(selector).then((found) => {
      if (!cancelled) setPresent(found);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selector, ...deps]);

  return present;
};
