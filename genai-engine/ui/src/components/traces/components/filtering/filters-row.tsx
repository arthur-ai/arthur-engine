import { ScrollArea } from "@base-ui-components/react/scroll-area";
import { Close, FilterList } from "@mui/icons-material";
import { IconButton, Paper, Stack, Typography } from "@mui/material";
import { useField, useStore } from "@tanstack/react-form";
import { Suspense, use, useRef } from "react";

import { useTracesStore } from "../../store";

import { DynamicEnumField, Field } from "./fields";
import { useAppForm, withForm } from "./hooks/form";
import { IncomingFilter } from "./mapper";
import { sharedFormOptions } from "./shared";
import { EnumOperators } from "./types";
import { getFieldLabel, getOperatorLabel } from "./utils";

import { NumberField } from "@/components/common/form/NumberField";
import { SelectField } from "@/components/common/form/SelectField";
import { cn } from "@/utils/cn";

type InferDynamicEnumArg<T extends DynamicEnumField<unknown>> =
  T extends DynamicEnumField<infer Arg> ? Arg : never;

type DynamicEnumArgMap<
  T extends Field[],
  TDynamic extends Extract<T[number], { type: "dynamic_enum" }> = Extract<
    T[number],
    { type: "dynamic_enum" }
  >
> = {
  [K in TDynamic["name"]]: InferDynamicEnumArg<TDynamic>;
};

export function createFilterRow<TFields extends Field[]>(
  fields: TFields,
  dynamicEnumArgMap: DynamicEnumArgMap<TFields>
) {
  const FiltersRow = () => {
    const scrollableRef = useRef<HTMLDivElement>(null);
    const [, store] = useTracesStore(() => null);

    const form = useAppForm({
      ...sharedFormOptions,
      onSubmit: async ({ value }) => {
        store.send({
          type: "setFilters",
          filters: value.config as IncomingFilter[],
        });
      },
    });

    const handleClose = () => {
      if (!scrollableRef.current) return;
      const offsetToEnd =
        scrollableRef.current.scrollWidth -
        scrollableRef.current.clientWidth -
        100;

      scrollableRef.current.scrollTo({ left: offsetToEnd, behavior: "smooth" });
    };

    return (
      <Paper variant="outlined" sx={{ p: 2 }}>
        <ScrollArea.Root
          render={
            <form
              onSubmit={(e) => {
                e.preventDefault();
                e.stopPropagation();
                form.handleSubmit();
              }}
            />
          }
          className="grid grid-cols-[1fr_min-content] gap-2 h-10"
        >
          <ScrollArea.Viewport
            ref={scrollableRef}
            className="p-1 bg-gray-50 border border-gray-200 rounded h-full has-[input:hover]:bg-gray-100 transition-colors duration-100"
          >
            <ScrollArea.Content className="flex flex-row gap-2 h-full text-xs">
              <form.Field mode="array" name="config">
                {(field) =>
                  field.state.value.map((item, index) => (
                    <FilterItem
                      key={index}
                      index={index}
                      onRemove={() => field.removeValue(index)}
                      onClose={handleClose}
                      form={form}
                    />
                  ))
                }
              </form.Field>

              <form.Field mode="array" name="config">
                {(field) => (
                  <input
                    placeholder={
                      !field.state.value.length
                        ? `Add filters to narrow down the results...`
                        : undefined
                    }
                    className="min-w-[200px] flex-1 outline-none placeholder:text-gray-600 text-xs h-full"
                    onFocus={() =>
                      field.pushValue({ name: "", operator: "", value: "" })
                    }
                  />
                )}
              </form.Field>
            </ScrollArea.Content>
          </ScrollArea.Viewport>
          <IconButton type="submit">
            <FilterList />
          </IconButton>
        </ScrollArea.Root>
      </Paper>
    );
  };

  const FilterItem = withForm({
    ...sharedFormOptions,
    props: {} as {
      index: number;
      onRemove: () => void;
      onClose: () => void;
    },
    render: function Render({ form, index, onRemove, onClose }) {
      const field = useField({ form, name: `config[${index}]` as const });

      const config = useStore(field.store, (state) => state.value);

      const { operators } =
        fields.find((field) => field.name === config.name) ?? {};

      const operatorItems = operators?.map((operator) => ({
        label: getOperatorLabel(operator),
        value: operator,
      }));

      const stage = (() => {
        switch (true) {
          case !!config.name && !!config.operator && config.value !== "":
            return 3;
          case !!config.name && !!config.operator:
            return 2;
          case !!config.name:
            return 1;
          default:
            return 0;
        }
      })();

      const handleOpenChange = (
        open: boolean,
        type: "name" | "operator" | "value"
      ) => {
        if (open) return;

        onClose();

        if (type === "name" && !config.name) return onRemove();
        if (type === "operator" && !config.operator) return onRemove();
        if (type === "value" && config.value === "") return onRemove();
      };

      return (
        <Stack direction="row" className="group shrink-0" data-stage={stage}>
          <form.AppField name={`config[${index}].name` as const}>
            {(field) => (
              <field.SelectField
                itemToStringLabel={getFieldLabel}
                defaultOpen={stage === 0}
                onOpenChangeComplete={(open) =>
                  handleOpenChange(open, "name" as const)
                }
              >
                <SelectField.Trigger className="rounded-none rounded-l group-data-[stage='0']:rounded-r">
                  <SelectField.Value />
                </SelectField.Trigger>
                <SelectField.Portal>
                  <SelectField.Positioner>
                    <SelectField.Popup>
                      <SelectField.List>
                        {fields.map(({ name }) => (
                          <SelectField.Item key={name} value={name}>
                            <SelectField.ItemText>
                              <Typography variant="body2">
                                {getFieldLabel(name)}
                              </Typography>
                            </SelectField.ItemText>
                          </SelectField.Item>
                        ))}
                      </SelectField.List>
                    </SelectField.Popup>
                  </SelectField.Positioner>
                </SelectField.Portal>
              </field.SelectField>
            )}
          </form.AppField>
          {stage >= 1 && (
            <form.AppField name={`config[${index}].operator` as const}>
              {(field) => (
                <field.SelectField
                  items={operatorItems}
                  defaultOpen={stage === 1}
                  onOpenChangeComplete={(open) =>
                    handleOpenChange(open, "operator" as const)
                  }
                >
                  <SelectField.Trigger className="rounded-none group-data-[stage='1']:rounded-r border-l-0">
                    <SelectField.Value />
                  </SelectField.Trigger>
                  <SelectField.Portal>
                    <SelectField.Positioner>
                      <SelectField.Popup>
                        <SelectField.List>
                          {operatorItems?.map(({ value }) => (
                            <SelectField.Item
                              key={value}
                              value={value}
                              className="min-w-[var(--anchor-width)]"
                            >
                              <SelectField.ItemText>
                                <Typography variant="body2">
                                  {getOperatorLabel(value)}
                                </Typography>
                              </SelectField.ItemText>
                            </SelectField.Item>
                          ))}
                        </SelectField.List>
                      </SelectField.Popup>
                    </SelectField.Positioner>
                  </SelectField.Portal>
                </field.SelectField>
              )}
            </form.AppField>
          )}
          {stage >= 2 && (
            <ValueInput
              form={form}
              index={index}
              onOpenChange={(open) => handleOpenChange(open, "value" as const)}
            />
          )}
          {stage === 3 && (
            <button
              onClick={onRemove}
              className="h-full aspect-square bg-gray-50 border border-gray-200 rounded-r border-l-0 grid place-items-center"
            >
              <Close sx={{ fontSize: 12 }} />
            </button>
          )}
        </Stack>
      );
    },
  });

  const ValueInput = withForm({
    ...sharedFormOptions,
    props: {} as {
      index: number;
      onOpenChange: (open: boolean) => void;
    },
    render: function Render({ form, index, onOpenChange }) {
      const field = useField({ form, name: `config[${index}]` as const });

      const config = useStore(field.store, (state) => state.value);

      const { name } = config;

      const fieldConfig = fields.find((field) => field.name === name);

      if (!fieldConfig) return null!;

      return (
        <form.AppField name={`config[${index}].value` as const}>
          {(field) => {
            if (fieldConfig.type === "enum")
              return (
                <field.SelectField
                  defaultOpen
                  onOpenChangeComplete={onOpenChange}
                  itemToStringLabel={fieldConfig.itemToStringLabel}
                  multiple={config.operator === EnumOperators.IN}
                >
                  <SelectField.Trigger className="rounded-l-none border-l-0 group-data-[stage='3']:rounded-r-none">
                    <SelectField.Value />
                  </SelectField.Trigger>
                  <SelectField.Portal>
                    <SelectField.Positioner>
                      <SelectField.Popup>
                        <SelectField.List>
                          {fieldConfig.options.map((option) => (
                            <SelectField.Item key={option} value={option}>
                              <SelectField.ItemText>
                                {fieldConfig.itemToStringLabel?.(option) ??
                                  option}
                              </SelectField.ItemText>
                            </SelectField.Item>
                          ))}
                        </SelectField.List>
                      </SelectField.Popup>
                    </SelectField.Positioner>
                  </SelectField.Portal>
                </field.SelectField>
              );

            if (fieldConfig.type === "dynamic_enum") {
              const multiple = config.operator === EnumOperators.IN;
              return (
                <field.SelectField
                  defaultOpen
                  onOpenChangeComplete={onOpenChange}
                  itemToStringLabel={fieldConfig.itemToStringLabel}
                  multiple={multiple}
                >
                  <SelectField.Trigger
                    className={cn(
                      "rounded-l-none border-l-0 group-data-[stage='3']:rounded-r-none",
                      fieldConfig.getTriggerClassName()
                    )}
                  >
                    {multiple ? (
                      <SelectField.Value>
                        {fieldConfig.renderValue}
                      </SelectField.Value>
                    ) : (
                      <SelectField.Value />
                    )}
                  </SelectField.Trigger>
                  <SelectField.Portal>
                    <SelectField.Positioner>
                      <SelectField.Popup>
                        <Suspense
                          fallback={
                            <SelectField.List>Loading...</SelectField.List>
                          }
                        >
                          <DynamicEnumInputList
                            form={form}
                            config={
                              fieldConfig as Extract<
                                TFields[number],
                                { type: "dynamic_enum" }
                              >
                            }
                          />
                        </Suspense>
                      </SelectField.Popup>
                    </SelectField.Positioner>
                  </SelectField.Portal>
                </field.SelectField>
              );
            }

            if (fieldConfig.type === "numeric") {
              return (
                <field.NumberField
                  min={fieldConfig.min}
                  max={fieldConfig.max}
                  onBlur={() => {
                    field.handleBlur();
                    onOpenChange(false);
                  }}
                  className="bg-white border border-gray-200 rounded-r group-data-[stage='3']:rounded-r-none border-l-0 overflow-hidden"
                >
                  <NumberField.Group className="flex h-full">
                    <NumberField.Input className="h-full" />
                  </NumberField.Group>
                </field.NumberField>
              );
            }
          }}
        </form.AppField>
      );
    },
  });

  const DynamicEnumInputList = withForm({
    ...sharedFormOptions,
    props: {} as {
      config: Extract<TFields[number], { type: "dynamic_enum" }>;
    },
    render: function Render({ config }) {
      let data: string[] = [];

      if (config.name in dynamicEnumArgMap) {
        data = use(
          config.promise(
            dynamicEnumArgMap[config.name as keyof typeof dynamicEnumArgMap]
          )
        );
      }

      return (
        <SelectField.List>
          {data.map((item) => (
            <SelectField.Item key={item} value={item}>
              <SelectField.ItemText>{item}</SelectField.ItemText>
            </SelectField.Item>
          ))}
        </SelectField.List>
      );
    },
  });

  return { FiltersRow, FilterItem, ValueInput, DynamicEnumInputList };
}
