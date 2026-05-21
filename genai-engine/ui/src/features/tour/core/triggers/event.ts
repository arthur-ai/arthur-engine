import type { TriggerFactory } from "../types";

/**
 * Advance when an event named `trigger.name` is emitted. We try the document
 * (window-level CustomEvent) first; consumers can also dispatch on document
 * directly. This intentionally does NOT subscribe to the tour bus to avoid
 * circular re-entry; bus events are an implementation detail of the engine.
 */
export const eventTrigger: TriggerFactory = ({ trigger, advance }) => {
  if (trigger.type !== "event") return () => {};

  const name = trigger.name;
  const handler = () => advance("event");

  document.addEventListener(name, handler);
  return () => document.removeEventListener(name, handler);
};
