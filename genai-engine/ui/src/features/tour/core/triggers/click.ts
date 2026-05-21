import type { TriggerFactory } from "../types";

/**
 * Advance when the target (or a custom selector) is clicked. If the trigger
 * declares a `selector`, that selector is observed; otherwise we listen on the
 * step's resolved target element.
 */
export const clickTrigger: TriggerFactory = ({ trigger, targetElement, advance }) => {
  if (trigger.type !== "click") return () => {};

  const handler = (event: Event) => {
    if (!event.target || !(event.target instanceof Element)) return;
    if (trigger.selector) {
      if (event.target.closest(trigger.selector)) advance("click");
    } else if (targetElement && (targetElement === event.target || targetElement.contains(event.target))) {
      advance("click");
    }
  };

  document.addEventListener("click", handler, true);
  return () => document.removeEventListener("click", handler, true);
};
