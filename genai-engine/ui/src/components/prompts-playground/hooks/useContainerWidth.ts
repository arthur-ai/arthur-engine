import { useEffect, useState, RefObject } from "react";

/**
 * Custom hook to detect container width using ResizeObserver
 * This enables container query-like behavior in React
 */
const useContainerWidth = (ref: RefObject<HTMLElement>) => {
  const [width, setWidth] = useState<number>(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });

    resizeObserver.observe(element);

    // Set initial width
    setWidth(element.getBoundingClientRect().width);

    return () => {
      resizeObserver.disconnect();
    };
  }, [ref]);

  return width;
};

export default useContainerWidth;
