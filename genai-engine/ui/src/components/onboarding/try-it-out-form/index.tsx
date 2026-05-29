import { useSuspenseQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { TryItOutFormLinear } from "./linear";
import type { TryItOutFormProps } from "./types";
import { TryItOutFormWizard } from "./wizard";

import { experimentVariantQueryOptions } from "@/hooks/useExperimentVariant";
import { preloadRecaptcha, setRecaptchaBadgeVisible } from "@/lib/recaptcha";

export { TryItOutFormLinear } from "./linear";
export { TryItOutFormWizard } from "./wizard";
export type { TryItOutSubmission } from "./schema";

const VARIANT_MAP = {
  wizard: TryItOutFormWizard,
  linear: TryItOutFormLinear,
};

export const TryItOutForm: React.FC<TryItOutFormProps> = (props) => {
  const { data } = useSuspenseQuery(experimentVariantQueryOptions({ experimentName: "onboarding-form-version" }));

  // Load reCAPTCHA and reveal its badge only while the form is mounted; hide it
  // again when the user leaves the form. Covers both form variants.
  useEffect(() => {
    preloadRecaptcha();
    setRecaptchaBadgeVisible(true);
    return () => setRecaptchaBadgeVisible(false);
  }, []);

  const variant = (data.value as keyof typeof VARIANT_MAP) ?? "linear";
  const VariantForm = VARIANT_MAP[variant];

  return <VariantForm {...props} />;
};
