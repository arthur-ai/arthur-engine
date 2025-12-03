import React from "react";

import { SearchBar } from "@/components/common/SearchBar";

interface DatasetsSearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export const DatasetsSearchBar: React.FC<DatasetsSearchBarProps> = ({
  value,
  onChange,
}) => {
  return (
    <SearchBar
      value={value}
      onChange={onChange}
      placeholder="Search datasets by name..."
    />
  );
};
