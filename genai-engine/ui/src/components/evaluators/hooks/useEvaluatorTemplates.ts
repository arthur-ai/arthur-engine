import { useMemo } from "react";

import evaluatorTemplatesData from "../data/evaluator-templates.json";
import type { EvaluatorTemplate } from "../types/evaluator-template";

/**
 * Hook that provides pre-defined evaluator templates
 */
export function useEvaluatorTemplates(): EvaluatorTemplate[] {
  return useMemo(() => evaluatorTemplatesData as EvaluatorTemplate[], []);
}
