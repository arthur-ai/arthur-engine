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

export type DynamicEnumField<TCtx> = {
  type: "dynamic_enum";
  operators: Operator[];
  itemToStringLabel: ((item: string) => string) | undefined;
  promise: (ctx: TCtx) => Promise<string[]>;
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

export type Field =
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  { name: string } & (PrimitiveFieldType | DynamicEnumField<any>);
