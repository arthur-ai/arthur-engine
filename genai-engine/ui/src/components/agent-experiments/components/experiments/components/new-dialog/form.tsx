import { z } from "zod";

export const FormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  dataset: z.object({
    id: z.string().min(1, "Dataset is required").nullable(),
    version: z.number().nullable(),
    filters: z.array(
      z.object({
        column: z.string().min(1, "Column is required"),
        value: z.string().min(1, "Value is required"),
      })
    ),
  }),
  endpointId: z.string().min(1, "Endpoint is required"),
  variableMapping: z.array(
    z
      .discriminatedUnion("source", [
        z.object({
          source: z.literal("dataset_column"),
          column: z.string().nullable(),
        }),
        z.object({
          source: z.literal("request"),
        }),
        z.object({
          source: z.literal("per_case"),
        }),
      ])
      .and(
        z.object({
          name: z.string(),
        })
      )
  ),
  evals: z
    .array(
      z.object({
        name: z.string(),
        version: z.string(),
      })
    )
    .min(1, "At least one evaluator is required"),
});

export type FormValues = z.infer<typeof FormSchema>;
