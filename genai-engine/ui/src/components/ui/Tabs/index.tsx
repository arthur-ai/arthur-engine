import { Tabs as BaseTabs } from "@base-ui-components/react/tabs";

import { cn } from "@/utils/cn";

const Root = ({ className, ...props }: BaseTabs.Root.Props) => {
  return (
    <BaseTabs.Root
      {...props}
      className={cn("bg-gray-50 rounded-xs", className)}
    />
  );
};

const List = ({ className, ...props }: BaseTabs.List.Props) => {
  return (
    <BaseTabs.List
      {...props}
      className={cn("relative z-0 flex gap-2 p-1 w-fit rounded-xs", className)}
    />
  );
};

const Tab = ({ className, ...props }: BaseTabs.Tab.Props) => {
  return (
    <BaseTabs.Tab
      {...props}
      className={cn(
        "flex h-8 items-center justify-center px-2 text-sm font-medium break-keep whitespace-nowrap text-gray-600 outline-none select-none before:inset-x-0 before:inset-y-1 before:rounded-sm before:-outline-offset-1 before:outline-blue-800 hover:text-gray-900 focus-visible:relative focus-visible:before:absolute focus-visible:before:outline-2 data-selected:text-gray-900",
        className
      )}
    />
  );
};

const Panel = ({ className, ...props }: BaseTabs.Panel.Props) => {
  return <BaseTabs.Panel {...props} className={cn("p-1 pt-0", className)} />;
};

const Indicator = ({ className, ...props }: BaseTabs.Indicator.Props) => {
  return (
    <BaseTabs.Indicator
      {...props}
      className={cn(
        "bg-gray-200 absolute top-1/2 left-0 h-(--active-tab-height) w-(--active-tab-width) translate-x-(--active-tab-left) -translate-y-1/2 z-[-1] rounded-xs transition-all duration-200 ease-in-out",
        className
      )}
    />
  );
};

export const Tabs = {
  Root,
  List,
  Tab,
  Panel,
  Indicator,
};
