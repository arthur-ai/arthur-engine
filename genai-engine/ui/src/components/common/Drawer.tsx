import { createContext, use, useState } from "react";
import BaseDrawer, { DrawerProps } from "@mui/material/Drawer";
import Button from "@mui/material/Button";
import { useRender } from "@base-ui-components/react/use-render";
import { mergeProps } from "@base-ui-components/react/merge-props";
import { useControlled } from "@mui/material/utils";

type DrawerContextType = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose: () => void;
};

const DrawerContext = createContext<DrawerContextType>({
  open: false,
  onOpenChange: () => {},
  onClose: () => {},
});

const useDrawer = () => {
  const context = use(DrawerContext);

  if (!context) {
    throw new Error("useDrawer must be used within a Drawer");
  }

  return context;
};

type RootProps = {
  children: React.ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  onClose?: () => void;
};

const Root = ({
  children,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
  onClose,
}: RootProps) => {
  const [open, setOpen] = useControlled({
    controlled: openProp,
    default: defaultOpen,
    name: "Drawer",
    state: "open",
  });

  const handleOpenChange = (open: boolean) => {
    setOpen(open);
    onOpenChange?.(open);
  };

  const handleClose = () => {
    setOpen(false);
    onClose?.();
  };

  return (
    <DrawerContext.Provider
      value={{ open, onOpenChange: handleOpenChange, onClose: handleClose }}
    >
      {children}
    </DrawerContext.Provider>
  );
};

Root.muiName = (BaseDrawer as any).muiName;

const Content = ({
  children,
  ...props
}: Omit<DrawerProps, "open" | "onClose">) => {
  const { open, onClose } = useDrawer();

  return (
    <BaseDrawer anchor="right" {...props} open={open} onClose={onClose}>
      {children}
    </BaseDrawer>
  );
};
Content.muiName = (BaseDrawer as any).muiName;

interface TriggerProps extends useRender.ComponentProps<typeof Button> {}

const Trigger = (props: TriggerProps) => {
  const { render, ...otherProps } = props;

  const { open, onOpenChange } = useDrawer();
  const element = useRender({
    defaultTagName: "button",
    render,
    props: mergeProps<"button">(otherProps, {
      onClick: () => onOpenChange(!open),
    }),
  });

  return element;
};

export const Drawer = Object.assign(Root, {
  Trigger,
  Content,
});
