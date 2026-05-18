import type { TryItOutFormProps } from "./types";
import { TryItOutFormWizard } from "./wizard";

export { TryItOutFormLinear } from "./linear";
export { TryItOutFormWizard } from "./wizard";
export type { TryItOutSubmission } from "./schema";

// TODO: replace with an Amplitude experiment lookup so that linear/wizard
// can be A/B-tested. For now: always render the wizard.
export const TryItOutForm: React.FC<TryItOutFormProps> = (props) => {
  return <TryItOutFormWizard {...props} />;
};
