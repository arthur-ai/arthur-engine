import { Field } from "./fields";
import { TRACE_FIELDS } from "./trace-fields";

export const SPAN_FIELDS = [
  ...TRACE_FIELDS,
] satisfies Field[];
