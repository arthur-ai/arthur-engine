import { formOptions } from "@tanstack/react-form";
import z from "zod";

const EvalsStepSchema = z.object({
  evalVariableMappings: z.array(
    z.object({
      variables: z.array(
        z
          .object({
            sourceType: z.enum(["dataset_column", "experiment_output"]),
            source: z.string(),
          })
          .refine((v) => v.sourceType === "experiment_output" || v.source.length > 0, {
            error: "Dataset column is required",
            path: ["source"],
          })
      ),
    })
  ),
});

const InfoStepSchema = z.object({
  info: z.object({
    name: z.string().min(1, { error: "Experiment name is required" }),
    description: z.string().optional(),
    prompt: z.object({
      name: z.string().min(1, { error: "Prompt is required" }),
      versions: z.array(z.number()).min(1, { error: "Select at least one prompt version" }),
    }),
    dataset: z.object({
      id: z.string().min(1, { error: "Dataset is required" }),
      version: z.number().min(1, { error: "Dataset version is required" }),
    }),
    evaluators: z.array(
      z.object({
        name: z.string().min(1),
        version: z.number().min(1),
      })
    ),
  }),
});

export const createExperimentModalFormOpts = formOptions({
  defaultValues: {
    section: "info" as "info" | "prompts" | "evals",
    info: {
      name: "",
      description: "",
      prompt: {
        name: "",
        versions: [] as number[],
      },
      dataset: {
        id: null as string | null,
        version: null as number | null,
      },
      evaluators: [] as {
        name: string;
        version: number | null;
      }[],
    },
    promptVariableMappings: [] as {
      /**
       * The source of the variable. Dataset column name.
       */
      source: string;
      /**
       * The target of the variable. Prompt variable name.
       */
      target: string;
    }[],
    evalVariableMappings: [] as {
      name: string;
      version: number;
      variables: {
        name: string;
        sourceType: "dataset_column" | "experiment_output";
        source: string;
      }[];
    }[],
  },
  validators: {
    onSubmit: ({ value, formApi }) => {
      if (value.section === "info") {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return formApi.parseValuesWithSchema(InfoStepSchema as any);
      }
      if (value.section === "evals") {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return formApi.parseValuesWithSchema(EvalsStepSchema as any);
      }
    },
  },
});

export type CreateExperimentModalFormValues = typeof createExperimentModalFormOpts.defaultValues;
