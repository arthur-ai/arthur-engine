import type { TriggerFactory } from "../types";

import { clickTrigger } from "./click";
import { eventTrigger } from "./event";
import { manualTrigger } from "./manual";
import { createTriggerRegistry } from "./registry";
import { visibleTrigger } from "./visible";

export { createTriggerRegistry } from "./registry";
export type { TriggerRegistry } from "./registry";

export function createDefaultTriggerRegistry() {
  const builtIns: Record<string, TriggerFactory> = {
    manual: manualTrigger,
    click: clickTrigger,
    visible: visibleTrigger,
    event: eventTrigger,
  };
  return createTriggerRegistry(builtIns);
}
