import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";

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
] as const satisfies Field[];
