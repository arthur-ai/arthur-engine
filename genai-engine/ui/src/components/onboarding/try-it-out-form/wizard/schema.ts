import { z } from "zod";

import type { TryItOutSubmission } from "../linear/schema";

export const identitySchema = z.object({
  firstName: z.string().trim().min(1, { error: "Required" }),
  lastName: z.string().trim().min(1, { error: "Required" }),
  email: z.email({ error: "Enter a valid work email" }),
  jobTitle: z.string().trim().min(1, { error: "Required" }),
  company: z.string().trim().min(1, { error: "Required" }),
});

export const aboutSchema = z
  .object({
    maturity: z.string().min(1, { error: "Pick one" }),
    brings: z.string().min(1, { error: "Pick one" }),
    bringsOther: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.brings === "other" && !data.bringsOther.trim()) {
      ctx.addIssue({ code: "custom", path: ["bringsOther"], error: "Please specify" });
    }
  });

export const discoverySchema = z
  .object({
    competitors: z.array(z.string()).min(1, { error: "Pick at least one" }),
    competitorOther: z.string(),
    attribution: z.string().min(1, { error: "Pick one" }),
    attributionOther: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.competitors.includes("other") && !data.competitorOther.trim()) {
      ctx.addIssue({ code: "custom", path: ["competitorOther"], error: "Please specify" });
    }
    if (data.attribution === "other" && !data.attributionOther.trim()) {
      ctx.addIssue({ code: "custom", path: ["attributionOther"], error: "Please specify" });
    }
  });

export type IdentityValues = z.infer<typeof identitySchema>;
export type AboutValues = z.infer<typeof aboutSchema>;
export type DiscoveryValues = z.infer<typeof discoverySchema>;

export type WizardValues = {
  identity: IdentityValues;
  about: AboutValues;
  discovery: DiscoveryValues;
};

export const wizardDefaultValues: WizardValues = {
  identity: { firstName: "", lastName: "", email: "", jobTitle: "", company: "" },
  about: { maturity: "", brings: "", bringsOther: "" },
  discovery: { competitors: [], competitorOther: "", attribution: "", attributionOther: "" },
};

export const flattenWizardValues = (values: WizardValues): TryItOutSubmission => ({
  firstName: values.identity.firstName,
  lastName: values.identity.lastName,
  email: values.identity.email,
  jobTitle: values.identity.jobTitle,
  company: values.identity.company,
  maturity: values.about.maturity,
  brings: values.about.brings,
  bringsOther: values.about.bringsOther,
  competitors: values.discovery.competitors,
  competitorOther: values.discovery.competitorOther,
  attribution: values.discovery.attribution,
  attributionOther: values.discovery.attributionOther,
});

/**
 * Walks the form's field-meta map and returns the leaf names (without group prefix)
 * of fields under the given group that currently have at least one error.
 * Used for ONBOARDING_WIZARD_STEP_SUBMIT_FAILED's invalid_fields property.
 */
export const getInvalidGroupFields = (fieldMeta: Record<string, { errors?: unknown[] } | undefined>, groupName: keyof WizardValues): string[] => {
  const prefix = `${groupName}.`;
  return Object.entries(fieldMeta)
    .filter(([name, meta]) => name.startsWith(prefix) && (meta?.errors?.length ?? 0) > 0)
    .map(([name]) => name.slice(prefix.length));
};
