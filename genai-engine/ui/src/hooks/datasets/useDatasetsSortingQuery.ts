import { useCallback, useState } from "react";

import { SortOrder } from "@/types/dataset";

export const useDatasetsSortingQuery = () => {
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const handleSort = useCallback(() => {
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
  }, []);

  return {
    sortOrder,
    handleSort,
  };
};
