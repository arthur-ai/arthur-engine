import type { ActionEmitEvent, TriggerFactory } from "../types";

/**
 * v1 action trigger. Listens on the engine's mitt bus for `action:emit` events
 * matching `trigger.name`. Replaces v0's `eventTrigger` (which round-tripped
 * through `document.addEventListener` for global, untyped CustomEvents).
 *
 * Consumers emit actions through `useTourAction()` / `engine.emitAction(...)`,
 * keeping the entire surface inside React context — no DOM globals.
 */
export const actionTrigger: TriggerFactory = ({ trigger, bus, advance }) => {
  if (trigger.type !== "action") return () => {};

  const name = trigger.name;
  const handler = (event: ActionEmitEvent) => {
    if (event.name === name) advance("action");
  };

  bus.on("action:emit", handler);
  return () => bus.off("action:emit", handler);
};
