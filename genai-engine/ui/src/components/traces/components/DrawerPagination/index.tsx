import { Button, ButtonGroup } from "@mui/material";

import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { usePaginationContext } from "../../stores/pagination-context";

export const DrawerPagination = () => {
  const context = usePaginationContext((state) => state.context);
  const [current, setDrawerTarget] = useDrawerTarget();

  if (!current) return null;
  if (context.type !== current.target)
    return (
      <span className="text-sm text-gray-400">
        Currently navigating on <code className="font-mono bg-gray-700 text-white px-1 py-0.5 rounded-md">{context.type}</code> level.
      </span>
    );

  if (!context.ids.length) return <span className="text-sm text-gray-400">No context available.</span>;

  const idx = current.id ? context.ids.indexOf(current.id) : -1;

  if (idx === -1) return <span className="text-sm text-gray-400">Current item not found in context.</span>;

  const hasNext = idx < context.ids.length - 1;
  const hasPrevious = idx > 0;

  const handlePrevious = () => {
    setDrawerTarget({ target: context.type, id: context.ids[idx - 1] });
  };

  const handleNext = () => {
    setDrawerTarget({ target: context.type, id: context.ids[idx + 1] });
  };

  return (
    <ButtonGroup size="small">
      <Button disabled={!hasPrevious} onClick={handlePrevious}>
        Previous
      </Button>
      <Button disabled>
        {idx + 1} of {context.ids.length}
      </Button>
      <Button disabled={!hasNext} onClick={handleNext}>
        Next
      </Button>
    </ButtonGroup>
  );
};
