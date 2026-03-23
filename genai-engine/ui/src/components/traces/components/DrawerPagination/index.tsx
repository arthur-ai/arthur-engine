import { Button, ButtonGroup } from "@mui/material";

type DrawerPaginationProps = {
  currentTarget: "trace" | "span" | "session" | "user" | null;
  currentId: string | null;
  contextType: "trace" | "span" | "session" | "user" | null;
  contextIds: string[];
  onNavigate: (target: "trace" | "span" | "session" | "user", id: string) => void;
};

export const DrawerPagination = ({ currentTarget, currentId, contextType, contextIds, onNavigate }: DrawerPaginationProps) => {
  if (!currentTarget || !currentId) return null;
  if (contextType !== currentTarget)
    return (
      <span className="text-sm text-gray-400 dark:text-gray-500">
        Currently navigating on <code className="font-mono bg-gray-700 dark:bg-gray-600 text-white px-1 py-0.5 rounded-md">{contextType}</code> level.
      </span>
    );

  if (!contextIds.length) return <span className="text-sm text-gray-400 dark:text-gray-500">No context available.</span>;

  const idx = currentId ? contextIds.indexOf(currentId) : -1;

  if (idx === -1) return <span className="text-sm text-gray-400 dark:text-gray-500">Current item not found in context.</span>;

  const hasNext = idx < contextIds.length - 1;
  const hasPrevious = idx > 0;

  const handlePrevious = () => {
    if (contextType) {
      onNavigate(contextType, contextIds[idx - 1]);
    }
  };

  const handleNext = () => {
    if (contextType) {
      onNavigate(contextType, contextIds[idx + 1]);
    }
  };

  return (
    <ButtonGroup size="small">
      <Button disabled={!hasPrevious} onClick={handlePrevious}>
        Previous
      </Button>
      <Button disabled>
        {idx + 1} of {contextIds.length}
      </Button>
      <Button disabled={!hasNext} onClick={handleNext}>
        Next
      </Button>
    </ButtonGroup>
  );
};
