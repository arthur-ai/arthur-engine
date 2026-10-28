import { Level } from "@arthur/shared-components";
import { parseAsString, useQueryState } from "nuqs";

export const useSelection = <T extends Level>(target: T) => {
  return useQueryState(
    `selection.${target}`,
    parseAsString.withDefault("").withOptions({
      history: "push",
    })
  );
};
