import { formOptions } from "@tanstack/react-form";

export const addToDatasetFormOptions = formOptions({
  defaultValues: {
    dataset: "",
    columns: [] as {
      name: string;
      value: string;
      path: string;
    }[],
  },
});
