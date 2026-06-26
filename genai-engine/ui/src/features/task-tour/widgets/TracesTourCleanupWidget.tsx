import { useTourEngine } from "@arthur/shared-components/tour";
import { useEffect } from "react";

import { useDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";

export function TracesTourCleanupWidget() {
  const engine = useTourEngine();
  const [, setDrawerTarget] = useDrawerTarget();

  useEffect(() => {
    const handleSectionComplete = (event: { sectionId: string }) => {
      if (event.sectionId !== "traces") return;
      void setDrawerTarget({ id: null });
    };

    engine.on("section:complete", handleSectionComplete);
    return () => {
      engine.off("section:complete", handleSectionComplete);
    };
  }, [engine, setDrawerTarget]);

  return null;
}
