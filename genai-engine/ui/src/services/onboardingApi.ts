import type { TryItOutSubmission } from "@/components/onboarding/try-it-out-form/schema";
import { createApiClient } from "@/lib/api";
import { ContentType } from "@/lib/api-client/api-client";

export type OnboardingFormVariant = "linear" | "wizard";

export interface OnboardingTryItOutFormData {
  first_name: string;
  last_name: string;
  email: string;
  job_title: string;
  company: string;
  maturity: string;
  brings: string;
  brings_other: string;
  competitors: string[];
  competitor_other: string;
  attribution: string;
  attribution_other: string;
}

export interface OnboardingSubmissionRequest {
  form_variant?: OnboardingFormVariant | null;
  form_data: OnboardingTryItOutFormData;
}

export interface OnboardingSubmissionResponse {
  id: string;
  created_at: string;
}

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

export async function createOnboardingSubmission(
  body: OnboardingSubmissionRequest
): Promise<OnboardingSubmissionResponse> {
  const client = createApiClient();
  const response = await client.request<OnboardingSubmissionResponse>({
    path: "/api/v2/onboarding/submissions",
    method: "POST",
    body,
    type: ContentType.Json,
    format: "json",
  });
  return response.data;
}
