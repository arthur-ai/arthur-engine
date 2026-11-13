import { SearchBar } from "@arthur/shared-components";
import React from "react";

interface DatasetsSearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export const DatasetsSearchBar: React.FC<DatasetsSearchBarProps> = ({ value, onChange }) => {
  return <SearchBar value={value} onChange={onChange} placeholder="Search datasets by name..." />;
};
