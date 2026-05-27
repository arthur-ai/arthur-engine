import type { TriggerFactory } from "../types";

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
