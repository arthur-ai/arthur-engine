import z from "zod";

// The form holds the cap as a dollar string; "" means no cap.
export const dailyCapSchema = z.string().refine(
  (value) => {
    if (value.trim() === "") return true;
    const dollars = Number(value);
    return Number.isFinite(dollars) && dollars > 0;
  },
  { error: "Enter an amount above 0, or leave it empty for no cap" }
);

export const dailyCapToUsd = (value: string): number | null => (value.trim() === "" ? null : Number(value));

export const usdToDailyCap = (cap: number | null | undefined): string => (cap == null ? "" : String(cap));
