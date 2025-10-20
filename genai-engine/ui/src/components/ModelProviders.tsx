import React, { useState, useEffect } from "react";

import { useApi } from "@/hooks/useApi";
import { ModelProviderResponse } from "@/lib/api";

export const ModelProviders: React.FC = () => {
  const api = useApi();
  const [providers, setProviders] = useState<ModelProviderResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModelProviders = async () => {
      try {
        setIsLoading(true);
        setError(null);

        if (!api) {
          throw new Error("API client not available");
        }

        const response =
          await api.api.getModelProvidersApiV1ModelProvidersGet();
        setProviders(response.data.providers || []);
      } catch (err) {
        console.error("Failed to fetch model providers:", err);
        setError(
          "Failed to load model providers. Please check your authentication."
        );
      } finally {
        setIsLoading(false);
      }
    };

    if (api) {
      fetchModelProviders();
    }
  }, [api]);

  const getProviderDisplayName = (provider: string): string => {
    const displayNames: Record<string, string> = {
      anthropic: "Anthropic",
      openai: "OpenAI",
      gemini: "Google Gemini",
    };
    return (
      displayNames[provider] ||
      provider.charAt(0).toUpperCase() + provider.slice(1)
    );
  };

  const getStatusBadge = (enabled: boolean) => {
    if (enabled) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <svg
            className="w-1.5 h-1.5 mr-1.5"
            fill="currentColor"
            viewBox="0 0 8 8"
          >
            <circle cx={4} cy={4} r={3} />
          </svg>
          Enabled
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <svg
            className="w-1.5 h-1.5 mr-1.5"
            fill="currentColor"
            viewBox="0 0 8 8"
          >
            <circle cx={4} cy={4} r={3} />
          </svg>
          Disabled
        </span>
      );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-900">
              Error loading model providers
            </h3>
            <div className="mt-2 text-sm text-red-800">
              <p>{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="text-lg font-medium text-black">
          Model Providers Configuration
        </h2>
        <p className="text-sm text-black">
          Manage and configure model providers to use LLM features.
        </p>
      </div>

      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-black uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-black uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-black uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {providers.length === 0 ? (
                  <tr>
                    <td
                      colSpan={3}
                      className="px-6 py-4 text-center text-sm text-black"
                    >
                      No model providers found
                    </td>
                  </tr>
                ) : (
                  providers.map((provider) => (
                    <tr key={provider.provider} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="text-sm font-medium text-black">
                            {getProviderDisplayName(provider.provider)}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(provider.enabled)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-black">
                        <button
                          className="text-blue-600 hover:text-blue-900 font-medium"
                          onClick={() => {
                            // TODO: Implement configuration action
                            console.log(
                              "Configure provider:",
                              provider.provider
                            );
                          }}
                        >
                          Configure
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
