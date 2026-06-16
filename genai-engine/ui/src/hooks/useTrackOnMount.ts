import { useEffect, useEffectEvent } from "react";

import { type AnalyticsEventName, type AnalyticsEvents, trackDynamic } from "@/services/analytics";

type Opts<E extends AnalyticsEventName> = AnalyticsEvents[E] extends undefined
  ? { eventName: E; eventProperties?: undefined }
  : { eventName: E; eventProperties: AnalyticsEvents[E] };

export const useTrackOnMount = <E extends AnalyticsEventName>({ eventName, eventProperties }: Opts<E>) => {
  const trackEvent = useEffectEvent(() => {
    // trackDynamic skips the generic gymnastics; the Opts type already
    // guarantees the name/properties pairing at the call site.
    trackDynamic(eventName, eventProperties as Record<string, unknown> | undefined);
  });

  useEffect(() => {
    trackEvent();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
};
