import { createPrimitiveField, Field } from "./fields";
import { Operators } from "./types";

export const SESSION_FIELDS = [
  createPrimitiveField({
    name: "trace_ids",
    type: "text",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    name: "session_ids",
    type: "text",
    operators: [Operators.EQUALS, Operators.IN],
  }),
  createPrimitiveField({
    name: "user_ids",
    type: "text",
    operators: [Operators.EQUALS, Operators.IN],
  }),
] as const satisfies readonly Field[];
