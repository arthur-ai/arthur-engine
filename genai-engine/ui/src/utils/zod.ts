import z from "zod";

export const jsonString = z
  .string()
  .transform((input, ctx) => {
    try {
      return JSON.parse(input);
    } catch (_) {
      ctx.issues.push({ code: "custom", message: "Invalid JSON", input });
      return z.NEVER;
    }
  })
  .pipe(z.json());
