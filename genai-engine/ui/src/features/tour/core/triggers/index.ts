import type { TriggerFactory } from "../types";

import { actionTrigger } from "./action";
import { clickTrigger } from "./click";
import { manualTrigger } from "./manual";
import { visibleTrigger } from "./visible";

/**
 * Built-in advance triggers, keyed by `AdvanceTrigger.type`. Passed to the
 * store as `initialTriggers` so the four built-ins are present before any
 * plugin's `registerTrigger` runs; plugins add custom keys on top.
 */
export function createDefaultTriggers(): Record<string, TriggerFactory> {
  return {
    manual: manualTrigger,
    click: clickTrigger,
    visible: visibleTrigger,
    action: actionTrigger,
  };
}
