import { Field } from "./fields";
import { TRACE_FIELDS } from "./trace-fields";

export const SPAN_FIELDS = TRACE_FIELDS.filter((f) => f.name !== "span_count") satisfies Field[];
