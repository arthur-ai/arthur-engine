import { formOptions } from "@tanstack/react-form";
import z from "zod";

import { Operator, Operators } from "./types";

type Config = {
  id: string;
  name: string;
  operator: Operator | "";
  value: string | string[];
};

export const sharedFormOptions = formOptions({
  defaultValues: {
    config: [] as Config[],
  },
});

export const validators = {
  name: z.string().min(1, "Field is required"),
  operator: z.enum(Object.values(Operators)),
  value: z.string().min(1, "Value is required"),
  valueArray: z.array(z.string()).min(1, "Value is required"),
  numeric: (min: number, max: number) => z.coerce.number().min(min).max(max),
};
