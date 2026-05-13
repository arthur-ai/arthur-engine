import { useMotionValue, type MotionValue } from "framer-motion";
import { useRef, type MouseEventHandler, type RefObject } from "react";

interface UsePointerTrackingResult<T extends HTMLElement> {
  ref: RefObject<T | null>;
  pointerX: MotionValue<number>;
  pointerY: MotionValue<number>;
  handleMouseMove: MouseEventHandler<T>;
  handleMouseLeave: MouseEventHandler<T>;
}

export function usePointerTracking<T extends HTMLElement = HTMLDivElement>(): UsePointerTrackingResult<T> {
  const ref = useRef<T>(null);
  const pointerX = useMotionValue(0.5);
  const pointerY = useMotionValue(0.5);

  const handleMouseMove: MouseEventHandler<T> = (event) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const nx = (event.clientX - rect.left) / rect.width;
    const ny = (event.clientY - rect.top) / rect.height;
    el.style.setProperty("--mouse-x", `${nx * 100}%`);
    el.style.setProperty("--mouse-y", `${ny * 100}%`);
    pointerX.set(nx);
    pointerY.set(ny);
  };

  const handleMouseLeave: MouseEventHandler<T> = () => {
    const el = ref.current;
    if (el) {
      el.style.setProperty("--mouse-x", "50%");
      el.style.setProperty("--mouse-y", "50%");
    }
    pointerX.set(0.5);
    pointerY.set(0.5);
  };

  return { ref, pointerX, pointerY, handleMouseMove, handleMouseLeave };
}
