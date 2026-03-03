import { capitalize } from "@mui/material";

import { createPrimitiveField, EnumOperators, Field, Operators, TextOperators } from "@arthur/shared-components";

export const CONTINUOUS_EVAL_FILTER_FIELDS = [
  createPrimitiveField({
    name: "name",
    type: "text",
    operators: [TextOperators.CONTAINS],
  }),
  createPrimitiveField({
    name: "llm_eval_name",
    type: "text",
    operators: [TextOperators.CONTAINS],
  }),
  createPrimitiveField({
    name: "enabled",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: ["true", "false"],
    itemToStringLabel: (option) => (option === "true" ? "Enabled" : "Disabled"),
  }),
  createPrimitiveField({
    name: "created_at",
    type: "date",
    operators: [Operators.GREATER_THAN, Operators.LESS_THAN],
  }),
] as const satisfies Field[];

export const CONTINUOUS_EVAL_RESULT_FIELDS = [
  createPrimitiveField({
    name: "continuous_eval_id",
    type: "text",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    name: "continuous_eval_id",
    type: "text",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    name: "eval_name",
    type: "text",
    operators: [TextOperators.CONTAINS],
  }),
  createPrimitiveField({
    name: "trace_id",
    type: "text",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    name: "annotation_score",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1].map(String),
    itemToStringLabel: (option) => option,
  }),
  createPrimitiveField({
    name: "run_status",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: ["pending", "passed", "running", "failed", "skipped", "error"],
    itemToStringLabel: (option) => capitalize(option),
  }),
  createPrimitiveField({
    name: "created_at",
    type: "date",
    operators: [Operators.GREATER_THAN, Operators.LESS_THAN],
  }),
] as const satisfies Field[];
