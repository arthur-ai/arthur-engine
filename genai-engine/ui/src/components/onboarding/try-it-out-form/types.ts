import type { TryItOutSubmission } from "./schema";

export interface TryItOutFormProps {
  onBack: () => void;
  onSubmit: (data: TryItOutSubmission) => void;
}
