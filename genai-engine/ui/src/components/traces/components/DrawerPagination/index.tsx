import { Button, ButtonGroup } from "@mui/material";
import { v4 as uuidv4 } from "uuid";

import { useTracesHistoryStore } from "../../stores/history.store";
import { usePaginationContext } from "../../stores/pagination-context";

export const DrawerPagination = () => {
  const context = usePaginationContext((state) => state.context);
  const current = useTracesHistoryStore((state) => state.current());
  const reset = useTracesHistoryStore((state) => state.reset);

  if (!current) return null;
  if (context.type !== current.target.type)
    return (
      <span className="text-sm text-gray-400">
        Currently navigating on <code className="font-mono bg-gray-700 text-white px-1 py-0.5 rounded-md">{context.type}</code> level.
      </span>
    );

  if (!context.ids.length) return <span className="text-sm text-gray-400">No context available.</span>;

  const idx = context.ids.indexOf(current.target.id.toString());

  if (idx === -1) return <span className="text-sm text-gray-400">Current item not found in context.</span>;

  const hasNext = idx < context.ids.length - 1;
  const hasPrevious = idx > 0;

  const handlePrevious = () => {
    reset([
      {
        key: uuidv4(),
        target: {
          type: context.type,
          id: context.ids[idx - 1],
        },
        ts: Date.now(),
      },
    ]);
  };

  const handleNext = () => {
    reset([
      {
        key: uuidv4(),
        target: {
          type: context.type,
          id: context.ids[idx + 1],
        },
        ts: Date.now(),
      },
    ]);
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
