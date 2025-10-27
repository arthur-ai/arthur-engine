import React from "react";

import { SearchBar } from "@/components/common/SearchBar";

interface DatasetSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  placeholder?: string;
}

export const DatasetSearchBar: React.FC<DatasetSearchBarProps> = ({
  value,
  onChange,
  onClear,
  placeholder = "Search across all columns...",
}) => {
  return (
    <SearchBar
      value={value}
      onChange={onChange}
      onClear={onClear}
      placeholder={placeholder}
    />
  );
};
