import { useForm, useStore } from "@tanstack/react-form";
import { useCallback, useMemo } from "react";

import type { RagProviderConfigurationResponse } from "@/lib/api-client/api-client";

interface FormValues {
  name: string;
  description: string;
  host_url: string;
  api_key: string;
}

type FieldValidator<TValue> = ({ value }: { value: TValue }) => string | undefined;

interface ProviderFieldValidators {
  name: {
    onChange: FieldValidator<string>;
  };
  description: {
    onChange: FieldValidator<string>;
  };
  host_url: {
    onChange: FieldValidator<string>;
  };
  api_key: {
    onChange: FieldValidator<string>;
  };
}

const hostnamePattern = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/;

function sanitizeHostUrl(url: string): string {
  return url
    .trim()
    .replace(/^https?:\/\//, "")
    .replace(/:\d+$/, "")
    .replace(/\/+$/, "");
}

function getInitialFormData(mode: "create" | "edit", initialData?: RagProviderConfigurationResponse): FormValues {
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
  const defaultValues = useMemo(() => getInitialFormData(mode, initialData), [mode, initialData]);

  const form = useForm({
    defaultValues,
  });

  const resetForm = useCallback(() => {
    form.reset(defaultValues);
  }, [form, defaultValues]);

  const normalizeHostUrl = useCallback((url: string): string => {
    const trimmed = url.trim();
    if (!trimmed) {
      return trimmed;
    }
    const withoutProtocol = trimmed.replace(/^https?:\/\//, "");
    return `https://${withoutProtocol}`;
  }, []);

  const fieldValidators = useMemo<ProviderFieldValidators>(() => {
    return {
      name: {
        onChange: ({ value }) => {
          if (!value.trim()) {
            return "Name is required";
          }
          if (value.length > 255) {
            return "Name must be less than 255 characters";
          }
          return undefined;
        },
      },
      description: {
        onChange: ({ value }) => {
          if (value.length > 1000) {
            return "Description must be less than 1000 characters";
          }
          return undefined;
        },
      },
      host_url: {
        onChange: ({ value }) => {
          if (!value.trim()) {
            return "Host URL is required";
          }
          const sanitized = sanitizeHostUrl(value);
          if (!sanitized || !hostnamePattern.test(sanitized)) {
            return "Please enter a valid host URL or domain";
          }
          return undefined;
        },
      },
      api_key: {
        onChange: ({ value }) => {
          const trimmed = value.trim();
          if (mode === "create" && trimmed === "") {
            return "API Key is required";
          }
          if (mode === "edit" && value !== "" && trimmed === "") {
            return "API Key is required";
          }
          return undefined;
        },
      },
    };
  }, [mode]);

  const values = useStore(form.store, (state) => state.values);

  const isFormValid = values.name.trim() !== "" && values.host_url.trim() !== "" && (mode === "edit" || values.api_key.trim() !== "");

  const validateForm = useCallback(async () => {
    await form.validateAllFields("submit");
    return form.store.state.isValid;
  }, [form]);

  return {
    form,
    values,
    fieldValidators,
    isFormValid,
    validateForm,
    resetForm,
    normalizeHostUrl,
  };
}
