import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";

import { createPrimitiveField, Field } from "./fields";
import { createFilterRow } from "./filters-row";
import { EnumOperators } from "./types";

export const SPAN_FIELDS = [
  createPrimitiveField({
    name: "span_types",
    type: "enum",
    operators: [EnumOperators.IN, EnumOperators.EQUALS],
    options: Object.values(OpenInferenceSpanKind),
    itemToStringLabel: undefined,
  }),
] as const satisfies Field[];

export const { FiltersRow } = createFilterRow(SPAN_FIELDS, {});
