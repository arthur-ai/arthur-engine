import { Field } from "./fields";
import { TRACE_FIELDS } from "./trace-fields";

export const SESSION_FIELDS = [...TRACE_FIELDS] as const satisfies Field[];
