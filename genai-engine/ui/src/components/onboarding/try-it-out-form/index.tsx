import { TryItOutFormLinear } from "./linear";
import type { TryItOutFormProps } from "./types";

export { TryItOutFormLinear } from "./linear";
export type { TryItOutSubmission } from "./schema";

export const TryItOutForm: React.FC<TryItOutFormProps> = (props) => {
  return <TryItOutFormLinear {...props} />;
};
