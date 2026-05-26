import { useMemo } from "react";

import type { TryItOutSubmission } from "@/components/onboarding/try-it-out-form/schema";
import type { TryItOutSubmitMeta } from "@/components/onboarding/try-it-out-form/types";
import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { createApiClient } from "@/lib/api";
import type { DemoTaskSignupResponse, OnboardingTryItOutFormData, TenantSignupRequest } from "@/lib/api-client/api-client";

export function toOnboardingFormData(data: TryItOutSubmission): OnboardingTryItOutFormData {
  return {
    first_name: data.firstName,
    last_name: data.lastName,
    email: data.email,
    job_title: data.jobTitle,
    company: data.company,
    maturity: data.maturity,
    brings: data.brings,
    brings_other: data.bringsOther,
    competitors: data.competitors,
    competitor_other: data.competitorOther,
    attribution: data.attribution,
    attribution_other: data.attributionOther,
  };
}

export interface CreateOnboardingSubmissionVariables {
  data: TryItOutSubmission;
  meta: TryItOutSubmitMeta;
}

interface UseCreateOnboardingSubmissionMutationOptions {
  onSuccess?: (data: DemoTaskSignupResponse, variables: CreateOnboardingSubmissionVariables) => void | Promise<void>;
  onError?: (error: Error, variables: CreateOnboardingSubmissionVariables) => void;
}

/** Public tenant signup; persists onboarding form data and provisions org/task/api key. */
export function useCreateOnboardingSubmissionMutation(options?: UseCreateOnboardingSubmissionMutationOptions) {
  const authApi = useApi();
  const api = useMemo(() => authApi ?? createApiClient(), [authApi]);

  return useApiMutation<DemoTaskSignupResponse, CreateOnboardingSubmissionVariables>({
    mutationFn: async ({ data, meta }) => {
      const payload: TenantSignupRequest = {
        form_variant: meta.formVariant,
        form_data: toOnboardingFormData(data),
      };
      const response = await api.api.createTenantSignupApiV2TenantSignupPost(payload);
      return response.data;
    },
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}
