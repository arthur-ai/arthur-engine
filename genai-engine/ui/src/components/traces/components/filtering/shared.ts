import { formOptions } from "@tanstack/react-form";

import { Operator } from "./types";

type Config = {
  name: string;
  operator: Operator | "";
  value: string | string[];
};

export const sharedFormOptions = formOptions({
  defaultValues: {
    config: [] as Config[],
  },
});
