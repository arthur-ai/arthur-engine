import React, { createContext, useCallback, useContext, useRef, useState } from "react";

interface NavigationGuardContextValue {
  registerBlocker: (blocked: boolean) => void;
  runGuardedNavigation: (proceed: () => void) => void;
  /** `true` while a blocked navigation is awaiting the user's confirmation. */
  isBlocking: boolean;
  /** Proceed with the deferred navigation (call from the confirm action). */
  confirmNavigation: () => void;
  cancelNavigation: () => void;
}

const NavigationGuardContext = createContext<NavigationGuardContextValue | null>(null);

export const NavigationGuardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const blockedRef = useRef(false);
  const pendingNavigationRef = useRef<(() => void) | null>(null);
  const [isBlocking, setIsBlocking] = useState(false);

  const registerBlocker = useCallback((blocked: boolean) => {
    blockedRef.current = blocked;
  }, []);

  const runGuardedNavigation = useCallback((proceed: () => void) => {
    if (blockedRef.current) {
      pendingNavigationRef.current = proceed;
      setIsBlocking(true);
    } else {
      proceed();
    }
  }, []);

  const confirmNavigation = useCallback(() => {
    const proceed = pendingNavigationRef.current;
    pendingNavigationRef.current = null;
    setIsBlocking(false);
    proceed?.();
  }, []);

  const cancelNavigation = useCallback(() => {
    pendingNavigationRef.current = null;
    setIsBlocking(false);
  }, []);

  return (
    <NavigationGuardContext.Provider value={{ registerBlocker, runGuardedNavigation, isBlocking, confirmNavigation, cancelNavigation }}>
      {children}
    </NavigationGuardContext.Provider>
  );
};

export const useNavigationGuard = (): NavigationGuardContextValue => {
  const ctx = useContext(NavigationGuardContext);
  if (!ctx) {
    throw new Error("useNavigationGuard must be used within a NavigationGuardProvider");
  }
  return ctx;
};
