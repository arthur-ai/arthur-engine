import { WarmupStatusPillView } from "@/components/common/warmup-status";
import { useEngineWarmupStatus } from "@/hooks/useEngineWarmupStatus";

/**
 * App-specific wrapper around `WarmupStatusPillView`. Mounted once at the app
 * root in `App.tsx`; renders nothing once the engine reports `"ready"`.
 */
export function EngineWarmupStatusPill() {
  const { data } = useEngineWarmupStatus();
  return <WarmupStatusPillView data={data} />;
}
