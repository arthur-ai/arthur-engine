import { Select as BaseSelect } from "@base-ui-components/react/select";
import { Paper } from "@mui/material";

import { useFieldContext } from "@/components/traces/components/filtering/hooks/form-context";
import { cn } from "@/utils/cn";
import { Children } from "react";

const Root = <Value, Multiple extends boolean>(
  props: BaseSelect.Root.Props<Value, Multiple>
) => {
  const field = useFieldContext<typeof props.value>();

  return (
    <BaseSelect.Root
      {...props}
      value={field.state.value}
      onValueChange={(value) => field.handleChange(value)}
    />
  );
};
const Trigger = ({ className, ...props }: BaseSelect.Trigger.Props) => {
  return (
    <BaseSelect.Trigger
      {...props}
      className={cn(
        "px-2 py-0.5 bg-white border rounded text-black border-gray-200 shrink-0 items-center flex",
        className
      )}
    />
  );
};
const Value = BaseSelect.Value;
const List = ({ className, ...props }: BaseSelect.List.Props) => {
  return (
    <BaseSelect.List
      {...props}
      className={cn(
        "max-h-(--available-height) text-xs flex flex-col gap-1 z-100",
        className
      )}
    />
  );
};
const Item = ({ className, children, ...props }: BaseSelect.Item.Props) => {
  return (
    <BaseSelect.Item
      {...props}
      className={cn(
        "items-center cursor-pointer data-highlighted:bg-gray-100 data-selected:bg-gray-200 data-selected:border data-selected:border-gray-300 p-1 rounded",
        className
      )}
    >
      <BaseSelect.ItemText>{children}</BaseSelect.ItemText>
    </BaseSelect.Item>
  );
};

const ItemText = BaseSelect.ItemText;
const ItemIndicator = BaseSelect.ItemIndicator;

const Portal = BaseSelect.Portal;
const Positioner = (props: BaseSelect.Positioner.Props) => {
  return (
    <BaseSelect.Positioner
      {...props}
      className="outline-none select-none z-100"
      alignItemWithTrigger={false}
      side="bottom"
    />
  );
};
const Popup = ({ className, ...props }: BaseSelect.Popup.Props) => {
  return (
    <BaseSelect.Popup
      {...props}
      render={<Paper variant="outlined" />}
      className={cn(
        "z-100 group p-1 origin-(--transform-origin) rounded-md bg-[canvas] transition-[transform,scale,opacity] data-ending-style:scale-90 data-[ending-style]:opacity-0 data-[side=none]:data-[ending-style]:transition-none data-[starting-style]:scale-90 data-[starting-style]:opacity-0 data-[side=none]:data-[starting-style]:scale-100 data-[side=none]:data-[starting-style]:opacity-100 data-[side=none]:data-[starting-style]:transition-none dark:shadow-none dark:outline-gray-300",
        className
      )}
    />
  );
};

export const SelectField = {
  Root,
  Trigger,
  Value,
  List,
  Item,
  ItemText,
  ItemIndicator,
  Portal,
  Positioner,
  Popup,
} as const;
