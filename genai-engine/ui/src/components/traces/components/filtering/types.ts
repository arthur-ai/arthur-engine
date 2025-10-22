import { z } from "zod";

export const ComparisonOperators = {
  LESS_THAN: "lt",
  LESS_THAN_OR_EQUAL: "lte",
  GREATER_THAN: "gt",
  GREATER_THAN_OR_EQUAL: "gte",
  EQUALS: "eq",
} as const;

export const EnumOperators = {
  IN: "in",
  NOT_IN: "not_in",
  EQUALS: "eq",
} as const;

export const Operators = {
  ...ComparisonOperators,
  ...EnumOperators,
} as const;

export type Operator = (typeof Operators)[keyof typeof Operators];

export type ComparisonOperator = (typeof ComparisonOperators)[keyof typeof ComparisonOperators];
export type EnumOperator = (typeof EnumOperators)[keyof typeof EnumOperators];

export const MetricFilterSchema = z.object({
  name: z.string().min(1),
  operator: z.enum(Object.values(Operators)).or(z.literal("")),
  value: z.union([z.string(), z.number(), z.array(z.string())]),
});

export type MetricFilterSchema = z.infer<typeof MetricFilterSchema>;
