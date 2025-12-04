import { createPrimitiveField, Field } from "./fields";
import { Operators } from "./types";

export const SESSION_FIELDS = [
  createPrimitiveField({
    name: "user_ids",
    type: "text",
    operators: [Operators.EQUALS],
  }),
] as const satisfies Field[];
