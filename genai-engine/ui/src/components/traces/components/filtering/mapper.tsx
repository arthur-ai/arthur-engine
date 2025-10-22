import { FilterableField } from "./fields";
import { Operator, Operators } from "./types";

export type IncomingFilter = {
  name: FilterableField;
  operator: Operator;
  value: string | string[];
};

const OPERATOR_TO_KEY_PART = new Map<Operator, string>([
  [Operators.IN, "in"],
  [Operators.NOT_IN, "not_in"],
  [Operators.EQUALS, "eq"],
  [Operators.LESS_THAN, "lt"],
  [Operators.LESS_THAN_OR_EQUAL, "lte"],
  [Operators.GREATER_THAN, "gt"],
  [Operators.GREATER_THAN_OR_EQUAL, "gte"],
]);

export const mapFiltersToRequest = (filters: IncomingFilter[]) => {
  const request: Record<string, string | number | string[]> = {};

  filters.forEach((filter) => {
    let key = filter.name;

    if (key === "span_types") {
      return (request[key] = [filter.value].flat());
    }

    if (key === "trace_ids") {
      return (request[key] = [filter.value].flat());
    }

    const keyPart = OPERATOR_TO_KEY_PART.get(filter.operator);

    if (keyPart) {
      key += `_${keyPart}`;
    }

    request[key] = isNaN(Number(filter.value))
      ? filter.value
      : Number(filter.value);
  });

  return request;
};
