import { formOptions } from "@tanstack/react-form";

import { Operator } from "./types";

export const sharedFormOptions = formOptions({
  defaultValues: {
    config: [] as {
      name: string;
      operator: Operator | "";
      value: string | string[];
    }[],
  },
});
