import { parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

const state = {
  show: parseAsStringEnum(["history"] as const),
  id: parseAsString.withDefault(""),
} as const;

export const useShowState = () => {
  return useQueryStates(state);
};
