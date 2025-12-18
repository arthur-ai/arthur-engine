import { createContext, useContext, useMemo } from "react";

import { Bucketer, defaultBucketer, makeBucketer, Thresholds } from "../utils/duration";

type BucketContextType = {
  bucketer: Bucketer;
};

const BucketContext = createContext<BucketContextType>({
  bucketer: defaultBucketer,
});

type BucketProviderProps = {
  children: React.ReactNode;
  thresholds: Thresholds;
};

export const BucketProvider = ({ children, thresholds }: BucketProviderProps) => {
  const bucketer = useMemo(() => makeBucketer(thresholds.p50, thresholds.p90), [thresholds]);

  return <BucketContext.Provider value={{ bucketer }}>{children}</BucketContext.Provider>;
};

/**
 * Returns the bucketer function to use to bucket durations. If no bucketer is provided, it will return the default bucketer.
 * @returns The bucketer function to use to bucket durations.
 */
export const useBucketer = () => {
  const context = useContext(BucketContext);

  if (!context) {
    return defaultBucketer;
  }

  return context.bucketer;
};
