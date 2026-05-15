import { z } from "zod";

export const onboardingSchema = z
  .object({
    firstName: z.string().trim().min(1, { error: "Required" }),
    lastName: z.string().trim().min(1, { error: "Required" }),
    email: z.email({ error: "Enter a valid work email" }),
    jobTitle: z.string().trim().min(1, { error: "Required" }),
    company: z.string().trim().min(1, { error: "Required" }),
    building: z.string().trim().min(1, { error: "Tell us a bit" }),
    maturity: z.string().min(1, { error: "Pick one" }),
    brings: z.string().min(1, { error: "Pick one" }),
    bringsOther: z.string(),
    competitors: z.array(z.string()).min(1, { error: "Pick at least one" }),
    competitorOther: z.string(),
    attribution: z.string().min(1, { error: "Pick one" }),
  })
  .superRefine((data, ctx) => {
    if (data.brings === "other" && !data.bringsOther.trim()) {
      ctx.addIssue({ code: "custom", path: ["bringsOther"], error: "Please specify" });
    }
    if (data.competitors.includes("other") && !data.competitorOther.trim()) {
      ctx.addIssue({ code: "custom", path: ["competitorOther"], error: "Please specify" });
    }
  });

export type TryItOutSubmission = z.infer<typeof onboardingSchema>;
