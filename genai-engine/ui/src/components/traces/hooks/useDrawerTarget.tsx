import { LEVELS } from "@arthur/shared-components";
import { createSerializer, parseAsString, parseAsStringLiteral, useQueryStates } from "nuqs";

const searchParams = {
  target: parseAsStringLiteral(LEVELS).withDefault("trace"),
  id: parseAsString,
};

export const serializeDrawerTarget = createSerializer(searchParams);

export const useDrawerTarget = () => {
  return useQueryStates(searchParams, { history: "push" });
};
