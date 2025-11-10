import React, { useCallback, useRef, useEffect } from "react";

interface ResizableSplitterProps {
  onResize: (newRatio: number) => void;
  minTopRatio: number;
  minBottomRatio: number;
}

const ResizableSplitter = ({ onResize, minTopRatio, minBottomRatio }: ResizableSplitterProps) => {
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
      const containerHeight = containerRect.height;
      const mouseY = e.clientY;
      const containerTop = containerRect.top;

      // Calculate the ratio based on mouse position relative to container
      const relativeY = mouseY - containerTop;
      let newRatio = relativeY / containerHeight;

      // Enforce minimum constraints
      newRatio = Math.max(minTopRatio, Math.min(1 - minBottomRatio, newRatio));

      // Throttle updates using requestAnimationFrame
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }

      rafRef.current = requestAnimationFrame(() => {
        onResize(newRatio);
      });
    },
    [onResize, minTopRatio, minBottomRatio]
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
      document.body.style.cursor = "row-resize";
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
      className="group cursor-row-resize bg-gray-200 hover:bg-gray-400 hover:shadow-sm active:bg-gray-500 transition-all"
      style={{
        height: "4px",
        width: "100%",
        marginTop: "4px",
        marginBottom: "4px",
        position: "relative",
        zIndex: 10,
      }}
      role="separator"
      aria-orientation="horizontal"
      aria-label="Resize messages and response sections"
    >
      <div
        className="transition-all group-hover:opacity-100 group-hover:bg-gray-600"
        style={{
          position: "absolute",
          top: "calc(50% - 1.5px)",
          left: "50%",
          transform: "translateX(-50%)",
          width: "40px",
          height: "1px",
          backgroundColor: "#4b5563",
          opacity: 0.9,
        }}
      />
      <div
        className="transition-all group-hover:opacity-100 group-hover:bg-gray-600"
        style={{
          position: "absolute",
          top: "calc(50% + 1.5px)",
          left: "50%",
          transform: "translateX(-50%)",
          width: "40px",
          height: "1px",
          backgroundColor: "#4b5563",
          opacity: 0.9,
        }}
      />
    </div>
  );
};

export default ResizableSplitter;
