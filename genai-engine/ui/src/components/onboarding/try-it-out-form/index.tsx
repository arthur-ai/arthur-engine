import { useSuspenseQuery } from "@tanstack/react-query";

import { TryItOutFormLinear } from "./linear";
import type { TryItOutFormProps } from "./types";
import { TryItOutFormWizard } from "./wizard";

import { experimentVariantQueryOptions } from "@/hooks/useExperimentVariant";

export { TryItOutFormLinear } from "./linear";
export { TryItOutFormWizard } from "./wizard";
export type { TryItOutSubmission } from "./schema";

const VARIANT_MAP = {
  wizard: TryItOutFormWizard,
  linear: TryItOutFormLinear,
};

export const TryItOutForm: React.FC<TryItOutFormProps> = (props) => {
  const { data } = useSuspenseQuery(experimentVariantQueryOptions({ experimentName: "onboarding-form-version" }));

  const variant = (data.value as keyof typeof VARIANT_MAP) ?? "linear";
  const VariantForm = VARIANT_MAP[variant];

  return <VariantForm {...props} />;
};
