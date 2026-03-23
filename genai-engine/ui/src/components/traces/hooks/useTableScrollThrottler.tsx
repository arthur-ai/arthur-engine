import { useThrottler } from "@tanstack/react-pacer";
import { useEffect, useEffectEvent, useRef } from "react";

type Params = {
  onOffsetReached: () => void;
  offsetThreshold?: number;
  enabled: boolean;
};

export const useTableScrollThrottler = ({ onOffsetReached, offsetThreshold = 50, enabled }: Params) => {
  const ref = useRef<HTMLDivElement | null>(null);

  const scrollThrottler = useThrottler(
    (containerRef?: HTMLDivElement | null) => {
      if (containerRef) {
        const { scrollHeight, scrollTop, clientHeight } = containerRef;
        const offset = scrollHeight - scrollTop - clientHeight;

        if (offset < offsetThreshold && enabled) onOffsetReached();
      }
    },
    {
      wait: 100,
    }
  );

  const onLoad = useEffectEvent(() => {
    scrollThrottler.flush();
    scrollThrottler.maybeExecute(ref.current);
  });

  useEffect(() => {
    onLoad();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { ref, execute: scrollThrottler.maybeExecute };
};
