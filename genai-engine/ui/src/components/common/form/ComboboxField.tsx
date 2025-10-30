import { Combobox as BaseCombobox } from "@base-ui-components/react/combobox";
import { Paper } from "@mui/material";

import { useFieldContext } from "@/components/traces/components/filtering/hooks/form-context";
import { cn } from "@/utils/cn";

const Root = <Value, Multiple extends boolean>(
  props: BaseCombobox.Root.Props<Value, Multiple>
) => {
  const field = useFieldContext<typeof props.value>();

  return (
    <BaseCombobox.Root
      {...props}
      value={field.state.value}
      onValueChange={(value) => field.handleChange(value)}
    />
  );
};

const Input = ({ className, ...props }: BaseCombobox.Input.Props) => {
  return (
    <BaseCombobox.Input
      {...props}
      className={cn(
        "w-full rounded text-sm font-normal border border-gray-200 pl-2 text-gray-900 bg-[canvas] focus:outline-2 focus:-outline-offset-1 focus:outline-blue-800",
        className
      )}
    />
  );
};

const Trigger = ({ className, ...props }: BaseCombobox.Trigger.Props) => {
  return (
    <BaseCombobox.Trigger
      {...props}
      className={cn(
        "px-2 py-0.5 bg-white border rounded text-black border-gray-200 shrink-0 items-center flex",
        className
      )}
    />
  );
};

const Clear = ({ className, ...props }: BaseCombobox.Clear.Props) => {
  return (
    <BaseCombobox.Clear
      {...props}
      className={cn(
        "flex h-10 w-6 items-center justify-center rounded bg-transparent p-0 text-gray-600 hover:text-gray-900",
        className
      )}
    />
  );
};

const Value = BaseCombobox.Value;

const Portal = BaseCombobox.Portal;

const Positioner = ({ className, ...props }: BaseCombobox.Positioner.Props) => {
  return (
    <BaseCombobox.Positioner
      {...props}
      className={cn("outline-none select-none z-100", className)}
      side="bottom"
      sideOffset={4}
    />
  );
};

const Popup = ({ className, ...props }: BaseCombobox.Popup.Props) => {
  return (
    <BaseCombobox.Popup
      {...props}
      render={<Paper variant="outlined" />}
      className={cn(
        "w-(--anchor-width) z-100 group p-1 origin-(--transform-origin) rounded-md bg-[canvas] transition-[transform,scale,opacity] data-ending-style:scale-90 data-[ending-style]:opacity-0 data-[side=none]:data-[ending-style]:transition-none data-[starting-style]:scale-90 data-[starting-style]:opacity-0 data-[side=none]:data-[starting-style]:scale-100 data-[side=none]:data-[starting-style]:opacity-100 data-[side=none]:data-[starting-style]:transition-none dark:shadow-none dark:outline-gray-300",
        className
      )}
    />
  );
};

const Empty = ({ className, ...props }: BaseCombobox.Empty.Props) => {
  return (
    <BaseCombobox.Empty
      {...props}
      className={cn(
        "px-4 py-2 text-xs leading-4 text-gray-600 empty:m-0 empty:p-0",
        className
      )}
    />
  );
};

const List = ({ className, children, ...props }: BaseCombobox.List.Props) => {
  return (
    <BaseCombobox.List
      {...props}
      className={cn(
        "max-h-(--available-height) text-xs flex flex-col gap-1 z-100",
        className
      )}
    >
      {children}
    </BaseCombobox.List>
  );
};

const Item = ({ className, children, ...props }: BaseCombobox.Item.Props) => {
  return (
    <BaseCombobox.Item
      {...props}
      className={cn(
        "items-center text-xs cursor-pointer data-highlighted:bg-gray-100 data-selected:bg-gray-200 data-selected:border data-selected:border-gray-300 p-1 rounded",
        className
      )}
    >
      {children}
    </BaseCombobox.Item>
  );
};

const ItemIndicator = BaseCombobox.ItemIndicator;

const Icon = ({ className, ...props }: BaseCombobox.Icon.Props) => {
  return (
    <BaseCombobox.Icon
      {...props}
      className={cn("flex items-center justify-center", className)}
    />
  );
};

const Chips = ({
  className,
  children,
  ref,
  ...props
}: BaseCombobox.Chips.Props & {
  ref?: React.RefObject<HTMLDivElement | null>;
}) => {
  return (
    <BaseCombobox.Chips
      {...props}
      ref={ref}
      className={cn(
        "flex flex-wrap items-center gap-0.5 rounded-md border px-1.5 py-1 bg-white border-gray-200 focus-within:outline-2 focus-within:-outline-offset-1 focus-within:outline-blue-800",
        className
      )}
    >
      {children}
    </BaseCombobox.Chips>
  );
};

const Chip = BaseCombobox.Chip;
const ChipRemove = BaseCombobox.ChipRemove;

export const ComboboxField = {
  Root,
  Input,
  Trigger,
  Clear,
  Value,
  Icon,
  Portal,
  Positioner,
  Popup,
  Empty,
  List,
  Item,
  ItemIndicator,
  Chips,
  Chip,
  ChipRemove,
} as const;
