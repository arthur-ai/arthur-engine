import { createPrimitiveField, Field } from "./fields";
import { TRACE_FIELDS } from "./trace-fields";
import { ComparisonOperators } from "./types";

export const SPAN_FIELDS = [
  ...TRACE_FIELDS,
  createPrimitiveField({
    name: "span_duration",
    type: "numeric",
    operators: [...Object.values(ComparisonOperators)],
    min: 0,
    max: Infinity,
  }),
] satisfies Field[];
