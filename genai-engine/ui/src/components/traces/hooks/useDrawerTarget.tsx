import { createParser, createSerializer, parseAsString, parseAsStringLiteral, useQueryStates } from "nuqs";

import { LEVELS } from "../constants";

const searchParams = {
  target: parseAsStringLiteral(LEVELS).withDefault("trace"),
  id: parseAsString,
};

export const serializeDrawerTarget = createSerializer(searchParams);

export const useDrawerTarget = () => {
  return useQueryStates(searchParams, { history: "push" });
};
