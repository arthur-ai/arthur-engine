import z from "zod";

export const jsonString = z.string().pipe(
  z.preprocess((input, ctx) => {
    try {
      return JSON.parse(input);
    } catch (_) {
      ctx.issues.push({ code: "custom", message: "Invalid JSON", input });
      return z.NEVER;
    }
  }, z.json())
);
