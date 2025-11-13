import React, { useCallback, useRef, useEffect } from "react";

interface HorizontalResizableSplitterProps {
  onResize: (newRatio: number) => void;
  minLeftRatio: number;
  minRightRatio: number;
}

const HorizontalResizableSplitter = ({ onResize, minLeftRatio, minRightRatio }: HorizontalResizableSplitterProps) => {
  const splitterRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLElement | null>(null);
  const isDraggingRef = useRef(false);
  const rafRef = useRef<number | null>(null);

  const findContainer = useCallback(() => {
    if (!splitterRef.current) return null;
    let parent = splitterRef.current.parentElement;
    while (parent && parent !== document.body) {
      const computedStyle = window.getComputedStyle(parent);
      if (computedStyle.position !== "static" || parent.classList.contains("flex")) {
        return parent;
      }
      parent = parent.parentElement;
    }
    return parent;
  }, []);

  useEffect(() => {
    containerRef.current = findContainer();
  }, [findContainer]);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDraggingRef.current || !containerRef.current || !splitterRef.current) return;

      const container = containerRef.current;
      const containerRect = container.getBoundingClientRect();
      const containerWidth = containerRect.width;
      const mouseX = e.clientX;
      const containerLeft = containerRect.left;

      // Calculate the ratio based on mouse position relative to container
      const relativeX = mouseX - containerLeft;
      let newRatio = relativeX / containerWidth;

      // Enforce minimum constraints
      newRatio = Math.max(minLeftRatio, Math.min(1 - minRightRatio, newRatio));

      // Throttle updates using requestAnimationFrame
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }

      rafRef.current = requestAnimationFrame(() => {
        onResize(newRatio);
      });
    },
    [onResize, minLeftRatio, minRightRatio]
  );

  const handleMouseUp = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    isDraggingRef.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  }, [handleMouseMove]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      isDraggingRef.current = true;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      // Set up global event listeners
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    },
    [handleMouseMove, handleMouseUp]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  return (
    <div
      ref={splitterRef}
      onMouseDown={handleMouseDown}
      className="group cursor-col-resize bg-gray-200 hover:bg-gray-400 hover:shadow-sm active:bg-gray-500 transition-all"
      style={{
        width: "4px",
        height: "100%",
        marginLeft: "4px",
        marginRight: "4px",
        position: "relative",
        zIndex: 10,
      }}
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize columns"
    >
      <div
        className="transition-all group-hover:opacity-100 group-hover:bg-gray-600"
        style={{
          position: "absolute",
          left: "calc(50% - 1.5px)",
          top: "50%",
          transform: "translateY(-50%)",
          height: "40px",
          width: "1px",
          backgroundColor: "#4b5563",
          opacity: 0.9,
        }}
      />
      <div
        className="transition-all group-hover:opacity-100 group-hover:bg-gray-600"
        style={{
          position: "absolute",
          left: "calc(50% + 1.5px)",
          top: "50%",
          transform: "translateY(-50%)",
          height: "40px",
          width: "1px",
          backgroundColor: "#4b5563",
          opacity: 0.9,
        }}
      />
    </div>
  );
};

export default HorizontalResizableSplitter;
