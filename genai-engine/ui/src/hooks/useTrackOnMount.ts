import { useEffect, useEffectEvent } from "react";

import { track } from "@/services/amplitude";

type Opts = {
  eventName: string;
  eventProperties?: Record<string, unknown>;
};

export const useTrackOnMount = ({ eventName, eventProperties }: Opts) => {
  const trackEvent = useEffectEvent(() => {
    track(eventName, eventProperties);
  });

  useEffect(() => {
    trackEvent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
};
