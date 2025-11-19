import { useState, useCallback } from "react";

import type { RagProviderConfigurationResponse } from "@/lib/api-client/api-client";

interface FormData {
  name: string;
  description: string;
  host_url: string;
  api_key: string;
}

interface FormErrors {
  name?: string;
  description?: string;
  host_url?: string;
  api_key?: string;
}

function getInitialFormData(mode: "create" | "edit", initialData?: RagProviderConfigurationResponse): FormData {
  if (mode === "edit" && initialData) {
    const urlWithoutProtocol = initialData.authentication_config.host_url.replace(/^https?:\/\//, "");
    return {
      name: initialData.name,
      description: initialData.description || "",
      host_url: urlWithoutProtocol,
      api_key: "",
    };
  }
  return {
    name: "",
    description: "",
    host_url: "",
    api_key: "",
  };
}

export function useProviderForm(mode: "create" | "edit", initialData?: RagProviderConfigurationResponse) {
  const [formData, setFormData] = useState<FormData>(() => getInitialFormData(mode, initialData));
  const [errors, setErrors] = useState<FormErrors>({});

  const resetForm = useCallback(() => {
    setFormData(getInitialFormData(mode, initialData));
    setErrors({});
  }, [mode, initialData]);

  const updateField = useCallback((field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  }, []);

  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Name is required";
    } else if (formData.name.length > 255) {
      newErrors.name = "Name must be less than 255 characters";
    }

    if (formData.description.length > 1000) {
      newErrors.description = "Description must be less than 1000 characters";
    }

    if (!formData.host_url.trim()) {
      newErrors.host_url = "Host URL is required";
    } else {
      const urlToValidate = formData.host_url
        .replace(/^https?:\/\//, "")
        .replace(/:\d+$/, "")
        .replace(/\/+$/, "");

      const hostnamePattern = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/;

      if (!hostnamePattern.test(urlToValidate) || urlToValidate.length === 0) {
        newErrors.host_url = "Please enter a valid host URL or domain";
      }
    }

    if (!formData.api_key.trim() && (mode === "create" || formData.api_key !== "")) {
      newErrors.api_key = "API Key is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, mode]);

  const normalizeHostUrl = useCallback((url: string): string => {
    const trimmed = url.trim();
    if (!trimmed) return trimmed;

    const withoutProtocol = trimmed.replace(/^https?:\/\//, "");
    return `https://${withoutProtocol}`;
  }, []);

  const isFormValid = formData.name.trim() !== "" && formData.host_url.trim() !== "" && (mode === "edit" || formData.api_key.trim() !== "");

  return {
    formData,
    errors,
    isFormValid,
    updateField,
    validateForm,
    resetForm,
    normalizeHostUrl,
  };
}
