import z, { ZodType } from "zod";

export const nullableInput = <Schema extends ZodType>(schema: Schema) => {
  return schema.nullable().transform((value, ctx) => {
    if (value === null) {
      ctx.addIssue({
        code: "invalid_type",
        expected: schema._zod.def.type,
        input: null,
      });
      return z.NEVER;
    }
    return value;
  });
};
