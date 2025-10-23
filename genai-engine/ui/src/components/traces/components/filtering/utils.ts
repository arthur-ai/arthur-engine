import { type Operator, Operators } from "./types";

const OPERATOR_TO_LABEL: Record<Operator, string> = {
  [Operators.LESS_THAN]: "<",
  [Operators.LESS_THAN_OR_EQUAL]: "≤",
  [Operators.GREATER_THAN]: ">",
  [Operators.GREATER_THAN_OR_EQUAL]: "≥",
  [Operators.EQUALS]: "=",
  [Operators.IN]: "In",
  [Operators.NOT_IN]: "Not In",
};

export const getOperatorLabel = (operator: Operator) => {
  return OPERATOR_TO_LABEL[operator] ?? operator;
};

const NAME_TO_LABEL = {
  query_relevance: "Query Relevance",
  tool_selection: "Tool Selection",
  span_types: "Span Types",
  response_relevance: "Response Relevance",
  trace_duration: "Trace Duration",
  tool_usage: "Tool Usage",
  trace_ids: "Trace IDs",
  user_ids: "User IDs",
} as const;

export const getFieldLabel = (name: string) => {
  return NAME_TO_LABEL[name as keyof typeof NAME_TO_LABEL] ?? name;
};

const ENUM_OPTION_TO_LABEL = {
  ["0"]: "NOT RELEVANT",
  ["1"]: "RELEVANT",
  ["2"]: "N/A",
} as const;

export const getEnumOptionLabel = (option: string) => {
  return (
    ENUM_OPTION_TO_LABEL[option as keyof typeof ENUM_OPTION_TO_LABEL] ?? option
  );
};

// export const filtersToRequest = (
//   filters: MetricFilterSchema[]
// ): DataResultFilter[] => {
//   return filters.map((filter) => {
//     const isNumerical =
//       Object.values(ComparisonOperators).includes(
//         filter.operator as ComparisonOperator
//       ) && !isNaN(Number(filter.value));

//     return {
//       field_name: filter.name,
//       op: OPERATOR_TO_DATA_RESULT_FILTER_OP[filter.operator as Operator],
//       value: isNumerical ? +filter.value : filter.value,
//     };
//   });
// };
