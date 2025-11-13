import { Settings } from "@mui/icons-material";
import React from "react";

import type { RagProviderConfigurationResponse } from "@/lib/api-client/api-client";

interface ProviderSelectorProps {
  selectedProviderId: string;
  onProviderChange: (providerId: string) => void;
  providers: RagProviderConfigurationResponse[];
  isLoadingProviders: boolean;
  onManageProviders: () => void;
  isExecuting: boolean;
}

export const ProviderSelector: React.FC<ProviderSelectorProps> = ({
  selectedProviderId,
  onProviderChange,
  providers,
  isLoadingProviders,
  onManageProviders,
  isExecuting,
}) => {
  return (
    <div>
      <label htmlFor="rag-provider" className="block text-sm font-medium text-gray-900 mb-2">
        RAG Provider
      </label>
      <div className="flex items-center space-x-2">
        {isLoadingProviders ? (
          <div className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-500">Loading providers...</div>
        ) : (
          <select
            id="rag-provider"
            value={selectedProviderId}
            onChange={(e) => onProviderChange(e.target.value)}
            className="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 truncate"
            disabled={isExecuting || providers.length === 0}
            aria-label="Select RAG provider"
            aria-describedby="provider-description"
          >
            <option value="">{providers.length === 0 ? "No providers configured" : "Select a RAG provider"}</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id} title={`${provider.name} (${provider.authentication_config.host_url})`}>
                {provider.name}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={onManageProviders}
          disabled={isExecuting}
          className="shrink-0 inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          aria-label="Manage RAG Providers"
          title="Manage RAG Providers"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>

      {!selectedProviderId && (
        <div className="text-center py-4 text-sm text-gray-600">
          {providers.length === 0 ? (
            <p>
              No RAG providers configured.{" "}
              <button onClick={onManageProviders} className="text-blue-600 hover:text-blue-800 underline">
                Add a provider
              </button>{" "}
              to get started.
            </p>
          ) : (
            <p>Select a RAG provider to continue</p>
          )}
        </div>
      )}
    </div>
  );
};
