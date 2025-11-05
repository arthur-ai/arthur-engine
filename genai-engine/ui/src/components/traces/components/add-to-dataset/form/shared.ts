import { formOptions } from "@tanstack/react-form";

export type Column = {
  name: string;
  value: string;
  path: string;
};

export const addToDatasetFormOptions = formOptions({
  defaultValues: {
    dataset: "",
    columns: [] as Column[],
  },
});
