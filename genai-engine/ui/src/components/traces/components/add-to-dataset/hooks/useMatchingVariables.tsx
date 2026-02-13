import { useMemo } from "react";

import { TransformVariableDefinition } from "../form/shared";

export type MatchStatus = "full-match" | "partial" | "no-match";

type Opts = {
  columnNames: string[];
  variables: TransformVariableDefinition[];
};

export const useMatchingVariables = ({ columnNames, variables }: Opts) => {
  const { matchingNames, unmatchedTransform } = useMemo(() => {
    const datasetNames = new Set(columnNames ?? []);
    const transformNames = variables?.map((v) => v.variable_name) ?? [];
    const transformNamesSet = new Set(transformNames);

    const matching = [...datasetNames].filter((name) => transformNamesSet.has(name));
    const unmatchedFromTransform = transformNames.filter((name) => !datasetNames.has(name));

    return {
      matchingNames: matching,
      unmatchedTransform: unmatchedFromTransform,
    };
  }, [columnNames, variables]);

  let matchStatus: MatchStatus = "no-match";
  if (matchingNames.length > 0 && unmatchedTransform.length === 0) {
    matchStatus = "full-match";
  } else if (matchingNames.length > 0 && unmatchedTransform.length > 0) {
    matchStatus = "partial";
  }

  return {
    matchingNames,
    unmatchedTransform,
    matchStatus,
    matchCount: matchingNames.length,
  };
};
