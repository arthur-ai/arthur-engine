import { type ExtendedOpenInferenceSpanKind, type TraceSpan } from "../tracesTypes";
import { parseMetricDetails } from "../utils";
import { type FilterableField } from "./fields";
import { type ComparisonOperator, EnumOperators, type MetricFilterSchema, type Operator, Operators } from "./types";

/**
 * Available combinations of comparison operators for a numeric metric
 */
export const ComparisonOperatorCombinations = new Map<Operator, Set<Operator>>([
  [Operators.LESS_THAN, new Set([Operators.GREATER_THAN, Operators.GREATER_THAN_OR_EQUAL])],
  [Operators.LESS_THAN_OR_EQUAL, new Set([Operators.GREATER_THAN, Operators.GREATER_THAN_OR_EQUAL])],
  [Operators.GREATER_THAN, new Set([Operators.LESS_THAN, Operators.LESS_THAN_OR_EQUAL])],
  [Operators.GREATER_THAN_OR_EQUAL, new Set([Operators.LESS_THAN, Operators.LESS_THAN_OR_EQUAL])],
  [Operators.EQUALS, new Set()],
]);

export const EnumOperatorCombinations = new Map<Operator, Set<Operator>>([
  [Operators.IN, new Set([Operators.NOT_IN])],
  [Operators.NOT_IN, new Set([Operators.IN])],
  [Operators.EQUALS, new Set()],
]);

export const canBeCombinedWith = (operator: Operator, withOperator: Operator): boolean => {
  if (ComparisonOperatorCombinations.has(operator)) {
    return ComparisonOperatorCombinations.get(operator)?.has(withOperator) ?? false;
  }

  if (EnumOperatorCombinations.has(operator)) {
    return EnumOperatorCombinations.get(operator)?.has(withOperator) ?? false;
  }
  return false;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type SpanFilterStrategy<T = any> = (_: { span: TraceSpan; filter: Omit<MetricFilterSchema, "value"> & { value: T } }) => boolean;

const numericComparisonHelper = ({ left, operator, right }: { left: number; right: number; operator: ComparisonOperator }) => {
  switch (operator) {
    case Operators.GREATER_THAN:
      return left > right;
    case Operators.LESS_THAN:
      return left < right;
    case Operators.GREATER_THAN_OR_EQUAL:
      return left >= right;
    case Operators.LESS_THAN_OR_EQUAL:
      return left <= right;
    case Operators.EQUALS:
      return left === right;
    default:
      return false;
  }
};

const spanTypesStrategy: SpanFilterStrategy<ExtendedOpenInferenceSpanKind> = ({ span, filter }) => {
  if (filter.operator === EnumOperators.EQUALS) {
    return span.span_kind === filter.value;
  }

  if (filter.operator === EnumOperators.IN) {
    return filter.value.includes(span.span_kind as string);
  }

  return false;
};

const queryRelevanceStrategy: SpanFilterStrategy<number> = ({ span, filter }) => {
  const metric = span.metric_results.find((m) => m.metric_type === "QueryRelevance");

  if (!metric || !filter.operator) return false;

  const details = parseMetricDetails(metric.details);

  if (!details || !details.query_relevance) return false;

  const score =
    details.query_relevance.reranker_relevance_score || details.query_relevance.bert_f_score || details.query_relevance.llm_relevance_score || 0;

  return numericComparisonHelper({ left: score, operator: filter.operator as ComparisonOperator, right: filter.value });
};

const responseRelevanceStrategy: SpanFilterStrategy<number> = ({ span, filter }) => {
  const metric = span.metric_results.find((m) => m.metric_type === "ResponseRelevance");

  if (!metric || !filter.operator) return false;

  const details = parseMetricDetails(metric.details);

  if (!details || !details.response_relevance) return false;

  const score =
    details.response_relevance.reranker_relevance_score ||
    details.response_relevance.bert_f_score ||
    details.response_relevance.llm_relevance_score ||
    0;

  return numericComparisonHelper({ left: score, operator: filter.operator as ComparisonOperator, right: filter.value });
};

export const SPAN_FILTERS_STRATEGIES = {
  span_types: spanTypesStrategy,
  query_relevance: queryRelevanceStrategy,
  response_relevance: responseRelevanceStrategy,
} as Record<FilterableField, SpanFilterStrategy>;
