import { z } from "zod";

export const datasetFormSchema = z.object({
  name: z
    .string()
    .min(1, "Dataset name is required")
    .max(100, "Dataset name must be less than 100 characters")
    .trim(),
  description: z
    .string()
    .max(500, "Description must be less than 500 characters")
    .optional()
    .or(z.literal("")),
});

export const columnNameSchema = z
  .string()
  .min(1, "Column name is required")
  .max(100, "Column name must be less than 100 characters")
  .trim();

export type DatasetFormValues = z.infer<typeof datasetFormSchema>;
