// UP-4390: shared signal for "this org has exhausted its LLM token credits."
// Any FE call site that triggers a backend completion can detect the 429
// TOKEN_LIMIT_EXCEEDED response and open the global <OutOfCreditsDialog>
// via this context — no need to render an ad-hoc inline error.

import React, { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";

import { TokenLimitExceededDetail } from "@/lib/api-errors";

interface OutOfCreditsContextValue {
  isOpen: boolean;
  detail: TokenLimitExceededDetail | null;
  show: (detail?: TokenLimitExceededDetail | null) => void;
  dismiss: () => void;
}

const OutOfCreditsContext = createContext<OutOfCreditsContextValue | undefined>(undefined);

export const OutOfCreditsProvider = ({ children }: { children: ReactNode }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [detail, setDetail] = useState<TokenLimitExceededDetail | null>(null);

  const show = useCallback((nextDetail?: TokenLimitExceededDetail | null) => {
    setDetail(nextDetail ?? null);
    setIsOpen(true);
  }, []);

  const dismiss = useCallback(() => {
    setIsOpen(false);
  }, []);

  const value = useMemo<OutOfCreditsContextValue>(() => ({ isOpen, detail, show, dismiss }), [isOpen, detail, show, dismiss]);

  return <OutOfCreditsContext.Provider value={value}>{children}</OutOfCreditsContext.Provider>;
};

export const useOutOfCreditsDialog = (): OutOfCreditsContextValue => {
  const ctx = useContext(OutOfCreditsContext);
  if (ctx === undefined) {
    throw new Error("useOutOfCreditsDialog must be used within an OutOfCreditsProvider");
  }
  return ctx;
};
