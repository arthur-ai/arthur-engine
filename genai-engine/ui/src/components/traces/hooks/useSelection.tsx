import { parseAsString, useQueryState } from "nuqs";

import { Level } from "../constants";

export const useSelection = <T extends Level>(target: T) => {
  return useQueryState(
    `selection.${target}`,
    parseAsString.withDefault("").withOptions({
      history: "push",
    })
  );
};
