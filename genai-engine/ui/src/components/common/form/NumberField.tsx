import { NumberField as BaseNumberField } from "@base-ui-components/react/number-field";

import { useFieldContext } from "@/components/traces/components/filtering/hooks/form-context";
import { cn } from "@/utils/cn";

const Root = (props: BaseNumberField.Root.Props) => {
  const field = useFieldContext<number | null>();

  return (
    <BaseNumberField.Root
      {...props}
      value={field.state.value}
      onValueChange={(value) => field.handleChange(value)}
    />
  );
};
const Group = BaseNumberField.Group;
const Input = ({ className, ...props }: BaseNumberField.Input.Props) => {
  return (
    <BaseNumberField.Input
      className={cn("bg-white h-full px-2 outline-none", className)}
      {...props}
    />
  );
};
const Increment = BaseNumberField.Increment;
const Decrement = BaseNumberField.Decrement;

export const NumberField = {
  Root,
  Group,
  Input,
  Increment,
  Decrement,
} as const;
