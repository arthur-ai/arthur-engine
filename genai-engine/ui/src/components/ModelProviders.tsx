import { Edit, Delete } from "@mui/icons-material";
import React, { useState, useEffect } from "react";

import { useApi } from "@/hooks/useApi";
import { ModelProviderResponse } from "@/lib/api-client/api-client";

export const ModelProviders: React.FC = () => {
  const api = useApi();
  const [providers, setProviders] = useState<ModelProviderResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    provider: ModelProviderResponse | null;
  }>({ isOpen: false, provider: null });
  const [isDeleting, setIsDeleting] = useState(false);
  const [editModal, setEditModal] = useState<{
    isOpen: boolean;
    provider: ModelProviderResponse | null;
  }>({ isOpen: false, provider: null });
  const [apiKey, setApiKey] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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
          Enabled
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          Disabled
        </span>
      );
    }
  };

  const handleDeleteClick = (provider: ModelProviderResponse) => {
    setDeleteModal({ isOpen: true, provider });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal.provider || !api) return;

    try {
      setIsDeleting(true);
      await api.api.setModelProviderApiV1ModelProvidersProviderDelete(
        deleteModal.provider.provider
      );

      // Refresh the providers list
      const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
      setProviders(response.data.providers || []);

      // Close modal
      setDeleteModal({ isOpen: false, provider: null });
    } catch (err) {
      console.error("Failed to delete model provider:", err);
      setError("Failed to delete model provider. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModal({ isOpen: false, provider: null });
  };

  const handleEditClick = (provider: ModelProviderResponse) => {
    setEditModal({ isOpen: true, provider });
    setApiKey(""); // Clear the API key field when opening
  };

  const handleEditSave = async () => {
    if (!editModal.provider || !api || !apiKey.trim()) return;

    try {
      setIsSaving(true);
      await api.api.setModelProviderApiV1ModelProvidersProviderPut(
        editModal.provider.provider,
        { api_key: apiKey.trim() }
      );

      // Refresh the providers list
      const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
      setProviders(response.data.providers || []);

      // Close modal and clear form
      setEditModal({ isOpen: false, provider: null });
      setApiKey("");
    } catch (err) {
      console.error("Failed to save model provider:", err);
      setError(
        "Failed to save model provider configuration. Please try again."
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditCancel = () => {
    setEditModal({ isOpen: false, provider: null });
    setApiKey("");
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
                        <div className="flex space-x-2">
                          <button
                            className="text-blue-600 hover:text-blue-900 p-1 rounded-md hover:bg-blue-50 transition-colors duration-200"
                            onClick={() => handleEditClick(provider)}
                            title="Configure provider"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          {provider.enabled && (
                            <button
                              className="text-red-600 hover:text-red-900 p-1 rounded-md hover:bg-red-50 transition-colors duration-200"
                              onClick={() => handleDeleteClick(provider)}
                              title="Delete provider"
                            >
                              <Delete className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal.isOpen && deleteModal.provider && (
        <div className="fixed inset-0 bg-gray-600/30 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full">
                <svg
                  className="w-6 h-6 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
              </div>
              <div className="mt-2 text-center">
                <h3 className="text-lg font-medium text-black">
                  Delete Model Provider
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-black">
                    Are you sure you want to delete{" "}
                    <span className="font-medium">
                      {getProviderDisplayName(deleteModal.provider.provider)}
                    </span>
                    ?
                  </p>
                  <p className="text-sm text-red-600 mt-2 font-medium">
                    ⚠️ Any agents or evals currently using this provider will no
                    longer work.
                  </p>
                </div>
              </div>
              <div className="flex space-x-3 mt-4">
                <button
                  type="button"
                  onClick={handleDeleteCancel}
                  disabled={isDeleting}
                  className="flex-1 bg-gray-300 text-black py-2 px-4 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeleteConfirm}
                  disabled={isDeleting}
                  className="flex-1 bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                >
                  {isDeleting ? (
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Deleting...
                    </div>
                  ) : (
                    "Delete"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit/Configure Modal */}
      {editModal.isOpen && editModal.provider && (
        <div className="fixed inset-0 bg-gray-600/30 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center justify-center w-12 h-12 mx-auto bg-blue-100 rounded-full">
                <Edit className="w-6 h-6 text-blue-600" />
              </div>
              <div className="mt-2 text-center">
                <h3 className="text-lg font-medium text-black">
                  Configure{" "}
                  {getProviderDisplayName(editModal.provider.provider)}
                </h3>
                <div className="mt-4">
                  <label
                    htmlFor="apiKey"
                    className="block text-sm font-medium text-black mb-2 text-left"
                  >
                    API Key
                  </label>
                  <input
                    type="password"
                    id="apiKey"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Enter your API key..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-black"
                    disabled={isSaving}
                    autoFocus
                  />
                  <p className="text-xs text-black mt-2 text-left">
                    Your API key will be securely stored and used to
                    authenticate with{" "}
                    {getProviderDisplayName(editModal.provider.provider)}.
                  </p>
                </div>
              </div>
              <div className="flex space-x-3 mt-6">
                <button
                  type="button"
                  onClick={handleEditCancel}
                  disabled={isSaving}
                  className="flex-1 bg-gray-300 text-black py-2 px-4 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleEditSave}
                  disabled={isSaving || !apiKey.trim()}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                >
                  {isSaving ? (
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Saving...
                    </div>
                  ) : (
                    "Save"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
