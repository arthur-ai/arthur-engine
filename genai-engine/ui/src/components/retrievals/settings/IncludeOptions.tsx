import React from "react";

interface IncludeOptionsProps {
  includeMetadata: boolean;
  includeVector: boolean;
  onIncludeMetadataChange: (checked: boolean) => void;
  onIncludeVectorChange: (checked: boolean) => void;
  isExecuting: boolean;
}

export const IncludeOptions: React.FC<IncludeOptionsProps> = React.memo(
  ({ includeMetadata, includeVector, onIncludeMetadataChange, onIncludeVectorChange, isExecuting }) => {
    return (
      <div>
        <h4 className="text-sm font-medium text-gray-900 mb-3">Include in Results</h4>
        <div className="space-y-2">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="includeMetadata"
              checked={includeMetadata}
              onChange={(e) => onIncludeMetadataChange(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={isExecuting}
            />
            <label htmlFor="includeMetadata" className="ml-2 text-sm text-gray-900">
              Metadata (distance, score, explainScore)
            </label>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="includeVector"
              checked={includeVector}
              onChange={(e) => onIncludeVectorChange(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={isExecuting}
            />
            <label htmlFor="includeVector" className="ml-2 text-sm text-gray-900">
              Vector embeddings
            </label>
          </div>
        </div>
      </div>
    );
  }
);
