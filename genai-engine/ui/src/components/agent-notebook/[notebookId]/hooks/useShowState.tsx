import { parseAsStringEnum, useQueryState } from "nuqs";

export const useShowState = () => {
  return useQueryState("show", parseAsStringEnum(["history"] as const));
};
