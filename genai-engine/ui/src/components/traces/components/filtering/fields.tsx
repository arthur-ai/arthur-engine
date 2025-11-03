import { type AutocompleteProps } from "@mui/material";

import { type Operator } from "./types";

export type NumericField = {
  type: "numeric";
  operators: Operator[];
  min?: number;
  max?: number;
};

export type EnumField = {
  type: "enum";
  operators: Operator[];
  options: string[];
  itemToStringLabel: ((item: string) => string) | undefined;
};

export type UseDataFn<TCtx> = (ctx: TCtx) => {
  data: string[];
  loading: boolean;
};

export type DynamicEnumField<TCtx> = {
  type: "dynamic_enum";
  operators: Operator[];
  itemToStringLabel: ((item: string) => string) | undefined;
  useData: UseDataFn<TCtx>;
  getTriggerClassName: () => string;
  renderValue: (value: string[]) => React.ReactNode;
};

export type TextField = {
  type: "text";
  operators: [Extract<Operator, "eq">];
};

export type FreeSoloField = {
  type: "free_solo";
  operators: Extract<Operator, "eq" | "in">[];
  getAutocompleteProps?: (
    value?: string | string[]
  ) => Partial<AutocompleteProps<string, boolean, boolean, boolean>>;
};

export type PrimitiveFieldType =
  | NumericField
  | EnumField
  | TextField
  | FreeSoloField;

export function createPrimitiveField<
  Type extends PrimitiveFieldType,
  const Name extends string
>(field: { name: Name } & Type) {
  return field;
}

export function createDynamicEnumField<TCtx, const Name extends string>(
  field: { name: Name } & DynamicEnumField<TCtx>
) {
  return field;
}

export function filterFields<
  const T extends readonly Field[],
  N extends FieldNames<T>
>(fields: T, excludedFields: N[]) {
  return fields.filter(
    (item): item is Exclude<T[number], { name: N }> =>
      !excludedFields.includes(item.name as N)
  );
}

export type Field =
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  { name: string } & (PrimitiveFieldType | DynamicEnumField<any>);

export type FieldNames<T extends readonly Field[]> = T[number]["name"];
