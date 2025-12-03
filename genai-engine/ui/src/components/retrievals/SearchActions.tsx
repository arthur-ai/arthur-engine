import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import SaveIcon from "@mui/icons-material/Save";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import React from "react";

interface SearchActionsProps {
  onExportConfig: () => void;
  onSubmit: (e: React.FormEvent) => void;
  isDisabled: boolean;
  isExecuting: boolean;
  hasQuery: boolean;
  onSaveConfig?: () => void;
}

export const SearchActions: React.FC<SearchActionsProps> = ({ onExportConfig, onSubmit, isDisabled, isExecuting, hasQuery, onSaveConfig }) => {
  const baseDisabled = isDisabled || isExecuting;

  const searchDisabled = baseDisabled || !hasQuery;

  return (
    <div className="flex justify-between items-center pt-4 border-t border-gray-200">
      <div className="flex space-x-1">
        <Tooltip title="Export Config">
          <span>
            <IconButton onClick={onExportConfig} disabled={baseDisabled} size="small">
              <FileDownloadOutlinedIcon />
            </IconButton>
          </span>
        </Tooltip>

        {onSaveConfig && (
          <Tooltip title="Save Config">
            <span>
              <IconButton onClick={onSaveConfig} disabled={baseDisabled} size="small">
                <SaveIcon />
              </IconButton>
            </span>
          </Tooltip>
        )}
      </div>

      <button
        onClick={onSubmit}
        disabled={searchDisabled}
        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isExecuting ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Searching...
          </>
        ) : (
          <>
            <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Search
          </>
        )}
      </button>
    </div>
  );
};
