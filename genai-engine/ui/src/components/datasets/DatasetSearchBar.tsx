import { SearchBar } from "@arthur/shared-components";
import React from "react";

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
  placeholder = "Search by row ID or across all columns...",
}) => {
  return <SearchBar value={value} onChange={onChange} onClear={onClear} placeholder={placeholder} />;
};
