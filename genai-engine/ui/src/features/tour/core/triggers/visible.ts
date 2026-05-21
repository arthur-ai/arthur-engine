import type { TriggerFactory } from "../types";

/**
 * Advance when the target enters the viewport above the configured threshold.
 * Uses IntersectionObserver. If the target is missing we no-op.
 */
export const visibleTrigger: TriggerFactory = ({ trigger, targetElement, advance }) => {
  if (trigger.type !== "visible" || !targetElement) return () => {};

  const observer = new IntersectionObserver(
    (entries) => {
      const entry = entries.find((e) => e.target === targetElement);
      if (entry?.isIntersecting) advance("visible");
    },
    {
      threshold: trigger.threshold ?? 0.5,
      rootMargin: trigger.rootMargin,
    }
  );

  observer.observe(targetElement);
  return () => observer.disconnect();
};
