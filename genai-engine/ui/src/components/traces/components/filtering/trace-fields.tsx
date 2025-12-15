import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { capitalize } from "@mui/material";

import { createPrimitiveField, Field } from "./fields";
import { Operators, type Operator } from "./types";
import { ComparisonOperators, EnumOperators, TextOperators } from "./types";
import { getEnumOptionLabel } from "./utils";

export const TRACE_FIELDS = [
  createPrimitiveField({
    name: "span_types",
    type: "enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    options: Object.values(OpenInferenceSpanKind),
    itemToStringLabel: undefined,
  }),
  createPrimitiveField({
    name: "query_relevance",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: 1,
  }),
  createPrimitiveField({
    name: "response_relevance",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: 1,
  }),
  createPrimitiveField({
    name: "trace_duration",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: Infinity,
  }),
  createPrimitiveField({
    name: "tool_selection",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1, 2].map(String),
    itemToStringLabel: getEnumOptionLabel,
  }),
  createPrimitiveField({
    name: "tool_usage",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1, 2].map(String),
    itemToStringLabel: getEnumOptionLabel,
  }),
  createPrimitiveField({
    type: "text",
    name: "trace_ids",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    type: "text",
    name: "session_ids",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    type: "text",
    name: "span_ids",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    type: "text",
    name: "user_ids",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    name: "annotation_score",
    type: "enum",
    operators: [EnumOperators.EQUALS],
    options: [0, 1].map(String),
    itemToStringLabel: (option) => (option === "0" ? "Unhelpful" : "Helpful"),
  }),
  createPrimitiveField({
    name: "span_name",
    type: "text",
    operators: [TextOperators.EQUALS, TextOperators.CONTAINS] as Extract<Operator, "eq" | "contains">[],
  }),
  createPrimitiveField({
    name: "status_code",
    type: "enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    options: ["Ok", "Error"],
    itemToStringLabel: (option) => (option === "Ok" ? "Pass" : "Fail"),
    type: "enum",
    name: "annotation_type",
    operators: [EnumOperators.EQUALS],
    options: ["human", "continuous_eval"],
    itemToStringLabel: (option) => option,
  }),
  createPrimitiveField({
    type: "enum",
    name: "continuous_eval_run_status",
    operators: [EnumOperators.EQUALS],
    options: ["pending", "passed", "running", "failed", "skipped", "error"],
    itemToStringLabel: (option) => capitalize(option),
  }),
  createPrimitiveField({
    type: "text",
    name: "continuous_eval_name",
    operators: [TextOperators.CONTAINS],
  }),
] as const satisfies Field[];
