import { type Operator, Operators } from "./types";

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
