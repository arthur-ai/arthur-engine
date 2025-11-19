import React from "react";

import { DistanceThreshold } from "./settings/DistanceThreshold";
import { HybridAlpha } from "./settings/HybridAlpha";
import { IncludeOptions } from "./settings/IncludeOptions";
import { ResultLimitInput } from "./settings/ResultLimitInput";
import type { SearchMethod, SearchSettings as SearchSettingsType } from "./types";

interface SearchSettingsProps {
  searchMethod: SearchMethod;
  settings: SearchSettingsType;
  onSettingsChange: (settings: SearchSettingsType) => void;
  isExecuting: boolean;
}

export const SearchSettings: React.FC<SearchSettingsProps> = ({ searchMethod, settings, onSettingsChange, isExecuting }) => {
  const handleLimitChange = (limit: number): void => {
    onSettingsChange({
      ...settings,
      limit,
    });
  };

  const handleDistanceChange = (distance: number): void => {
    onSettingsChange({
      ...settings,
      distance,
    });
  };

  const handleAlphaChange = (alpha: number): void => {
    onSettingsChange({
      ...settings,
      alpha,
    });
  };

  const handleIncludeMetadataChange = (checked: boolean): void => {
    onSettingsChange({
      ...settings,
      includeMetadata: checked,
    });
  };

  const handleIncludeVectorChange = (checked: boolean): void => {
    onSettingsChange({
      ...settings,
      includeVector: checked,
    });
  };

  return (
    <div className="space-y-4">
      <ResultLimitInput limit={settings.limit} onChange={handleLimitChange} isExecuting={isExecuting} />

      {(searchMethod === "nearText" || searchMethod === "hybrid") && (
        <DistanceThreshold distance={settings.distance} onChange={handleDistanceChange} isExecuting={isExecuting} />
      )}

      {searchMethod === "hybrid" && <HybridAlpha alpha={settings.alpha} onChange={handleAlphaChange} isExecuting={isExecuting} />}

      <IncludeOptions
        includeMetadata={settings.includeMetadata}
        includeVector={settings.includeVector}
        onIncludeMetadataChange={handleIncludeMetadataChange}
        onIncludeVectorChange={handleIncludeVectorChange}
        isExecuting={isExecuting}
      />
    </div>
  );
};
