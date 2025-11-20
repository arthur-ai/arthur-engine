import { ScrollArea } from "@base-ui-components/react/scroll-area";
import { Close, Search } from "@mui/icons-material";
import { Button, Paper, Stack, TextField } from "@mui/material";
import { useField, useStore } from "@tanstack/react-form";
import { useMemo, useRef } from "react";
import { v4 as uuidv4 } from "uuid";

import { useFilterStore } from "../../stores/filter.store";

import { DynamicEnumField, Field } from "./fields";
import { useAppForm, withForm } from "./hooks/form";
import { IncomingFilter } from "./mapper";
import { canBeCombinedWith } from "./rules";
import { sharedFormOptions, validators } from "./shared";
import { EnumOperators, Operator } from "./types";
import { getFieldLabel, getOperatorLabel } from "./utils";

import { NumberField } from "@/components/common/form/NumberField";

const ROW_SCROLL_OFFSET = 100;

type InferDynamicEnumArg<Field extends DynamicEnumField<unknown>> = Field extends DynamicEnumField<infer Arg> ? Arg : never;

type ExtractFieldsByType<Fields extends Field[], Type extends Field["type"]> = Extract<Fields[number], { type: Type }>;

type DynamicEnumArgMap<
  Fields extends Field[],
  Dynamic extends ExtractFieldsByType<Fields, "dynamic_enum"> = ExtractFieldsByType<Fields, "dynamic_enum">,
> = {
  [K in Dynamic["name"]]: InferDynamicEnumArg<Dynamic>;
};

export function createFilterRow<TFields extends Field[]>(fields: TFields, dynamicEnumArgMap: DynamicEnumArgMap<TFields>) {
  const FiltersRow = () => {
    const scrollableRef = useRef<HTMLDivElement>(null);
    const setFilters = useFilterStore((state) => state.setFilters);

    const isFilterComplete = (item: { name: string; operator: Operator | ""; value: string | string[] }): boolean => {
      // Check if name is non-empty
      if (!item.name || item.name.trim() === "") {
        return false;
      }

      // Check if operator is non-empty and valid (not just "")
      if (!item.operator) {
        return false;
      }

      // Check if value is non-empty (string or array)
      if (Array.isArray(item.value)) {
        return item.value.length > 0;
      }
      return typeof item.value === "string" && item.value.trim() !== "";
    };

    const form = useAppForm({
      ...sharedFormOptions,
      onSubmit: async ({ value }) => {
        // Filter out incomplete filters before mapping and setting them
        const completeFilters = value.config.filter(isFilterComplete);

        setFilters(completeFilters.map(({ id: _, ...item }) => item) as IncomingFilter[]);
      },
    });

    const handleClose = () => {
      if (!scrollableRef.current) return;
      const offsetToEnd = scrollableRef.current.scrollWidth - scrollableRef.current.clientWidth - ROW_SCROLL_OFFSET;

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
          className="grid grid-cols-[1fr_max-content] gap-2"
        >
          <ScrollArea.Viewport
            ref={scrollableRef}
            className="p-2 bg-gray-50 border border-gray-200 rounded h-full has-[input:hover]:bg-gray-100 transition-colors duration-100"
          >
            <ScrollArea.Content className="flex flex-row gap-2 h-full text-xs">
              <form.Field mode="array" name="config">
                {(field) =>
                  field.state.value.map((item, index) => (
                    <FilterItem key={item.id} index={index} onRemove={() => field.removeValue(index)} onClose={handleClose} form={form} />
                  ))
                }
              </form.Field>

              <form.Field mode="array" name="config">
                {(field) => (
                  <input
                    placeholder={!field.state.value.length ? `Add filters to narrow down the results...` : undefined}
                    className="min-w-[200px] flex-1 outline-none placeholder:text-gray-600 text-xs h-full"
                    onFocus={() => field.pushValue({ name: "", operator: "", value: "", id: uuidv4() })}
                  />
                )}
              </form.Field>
            </ScrollArea.Content>
          </ScrollArea.Viewport>
          <form.Subscribe selector={(state) => state.canSubmit}>
            {(canSubmit) => (
              <Button
                type="submit"
                disabled={!canSubmit}
                variant="outlined"
                sx={{
                  alignSelf: "center",
                }}
                startIcon={<Search />}
              >
                Filter
              </Button>
            )}
          </form.Subscribe>
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
      const allMetrics = useStore(form.store, (state) => state.values.config.slice(0, index));
      const field = useField({ form, name: `config[${index}]` as const });

      const config = useStore(field.store, (state) => state.value);

      const operatorItems = useMemo(
        () => getAvailableOperators(allMetrics, config?.name ?? "")?.map((operator) => operator),
        [allMetrics, config?.name]
      );

      const stage = (() => {
        if (!config) return 0;
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

      return (
        <Stack direction="row" className="group shrink-0" data-stage={stage}>
          <form.AppField
            name={`config[${index}].name` as const}
            validators={{
              onMount: validators.name,
              onChange: validators.name,
            }}
          >
            {(field) => (
              <field.MaterialAutocompleteField
                disablePortal
                options={fields.map(({ name }) => name)}
                getOptionLabel={getFieldLabel}
                size="small"
                onClose={() => {
                  field.handleBlur();
                  onClose();
                }}
                sx={{
                  width: 200,
                  "& .MuiAutocomplete-inputRoot": {
                    borderTopRightRadius: 0,
                    borderBottomRightRadius: 0,
                    "& fieldset": {
                      borderRightWidth: 0,
                    },
                  },
                }}
                renderInput={(params) => <TextField {...params} variant="filled" label="Field" />}
              />
            )}
          </form.AppField>

          {stage >= 1 && (
            <form.AppField
              name={`config[${index}].operator` as const}
              validators={{
                onMount: validators.operator,
                onChange: validators.operator,
              }}
            >
              {(field) => (
                <field.MaterialAutocompleteField
                  disablePortal
                  options={operatorItems}
                  multiple={false}
                  getOptionLabel={getOperatorLabel}
                  onClose={() => {
                    field.handleBlur();
                    onClose();
                  }}
                  onChange={(_, value) => {
                    const isMultiple = value === EnumOperators.IN;

                    form.resetField(`config[${index}].value`);
                    form.setFieldValue(`config[${index}].value`, isMultiple ? [] : "");
                  }}
                  size="small"
                  sx={{
                    width: 150,
                    "& .MuiAutocomplete-inputRoot": {
                      borderRadius: 0,
                      "& fieldset": {
                        borderInlineWidth: 0,
                      },
                    },
                  }}
                  renderInput={(params) => <TextField {...params} variant="filled" label="Operator" />}
                />
              )}
            </form.AppField>
          )}
          {stage >= 2 && <ValueInput form={form} index={index} onClose={onClose} />}
          <Button size="small" variant="outlined" color="error" disableElevation onClick={onRemove} className="rounded-l-none!">
            <Close sx={{ fontSize: 16 }} />
          </Button>
        </Stack>
      );
    },
  });

  const ValueInput = withForm({
    ...sharedFormOptions,
    props: {} as {
      index: number;
      onClose: () => void;
    },
    render: function Render({ form, index, onClose }) {
      const field = useField({ form, name: `config[${index}]` as const });

      const config = useStore(field.store, (state) => state.value);

      const { name } = config;

      const fieldConfig = fields.find((field) => field.name === name);

      if (!fieldConfig) return null;

      let fieldValidators = {};
      if (fieldConfig.type === "enum" || fieldConfig.type === "dynamic_enum") {
        const multiple = config.operator === EnumOperators.IN;
        fieldValidators = {
          onMount: multiple ? validators.valueArray : validators.value,
          onChange: multiple ? validators.valueArray : validators.value,
        };
      } else if (fieldConfig.type === "numeric") {
        fieldValidators = {
          onMount: validators.numeric(fieldConfig.min ?? -Infinity, fieldConfig.max ?? Infinity),
          onChange: validators.numeric(fieldConfig.min ?? -Infinity, fieldConfig.max ?? Infinity),
        };
      } else if (fieldConfig.type === "text") {
        fieldValidators = {
          onMount: validators.value,
          onChange: validators.value,
        };
      }

      return (
        <form.AppField key={index} name={`config[${index}].value` as const} validators={fieldValidators}>
          {(field) => {
            if (fieldConfig.type === "enum") {
              const multiple = config.operator === EnumOperators.IN;
              return (
                <field.MaterialAutocompleteField
                  disablePortal
                  options={fieldConfig.options}
                  getOptionLabel={(option) => fieldConfig.itemToStringLabel?.(option) ?? option}
                  multiple={multiple}
                  onClose={onClose}
                  size="small"
                  sx={{
                    width: multiple ? "max-content" : 200,
                    minWidth: 200,
                    "& .MuiAutocomplete-inputRoot": {
                      borderRadius: 0,
                      "& fieldset": {
                        borderInlineWidth: 0,
                      },
                    },
                  }}
                  limitTags={1}
                  renderInput={(params) => <TextField {...params} variant="filled" label="Value" />}
                />
              );
            }

            if (fieldConfig.type === "dynamic_enum") {
              return (
                <DynamicEnumInput
                  form={form}
                  config={fieldConfig as Extract<TFields[number], { type: "dynamic_enum" }>}
                  index={index}
                  onClose={onClose}
                />
              );
            }

            if (fieldConfig.type === "numeric") {
              return (
                <field.NumberField
                  onBlur={() => {
                    field.handleBlur();
                    onClose();
                  }}
                  min={fieldConfig.min}
                  max={fieldConfig.max}
                  className=" overflow-hidden"
                >
                  <NumberField.Group className="flex h-full">
                    <NumberField.Input className="h-full" render={<TextField variant="filled" label="Value" size="small" />} />
                  </NumberField.Group>
                </field.NumberField>
              );
            }

            if (fieldConfig.type === "text") {
              return (
                <TextField
                  variant="filled"
                  label="Value"
                  size="small"
                  value={field.state.value || ""}
                  onChange={(e) => {
                    field.handleChange(e.target.value);
                  }}
                  onBlur={() => {
                    field.handleBlur();
                    onClose();
                  }}
                  sx={{
                    width: 200,
                    "& .MuiAutocomplete-inputRoot": {
                      borderRadius: 0,
                      "& fieldset": {
                        borderInlineWidth: 0,
                      },
                    },
                  }}
                />
              );
            }
          }}
        </form.AppField>
      );
    },
  });

  const DynamicEnumInput = withForm({
    ...sharedFormOptions,
    props: {} as {
      config: Extract<TFields[number], { type: "dynamic_enum" }>;
      index: number;
      onClose: () => void;
    },
    render: function Render({ config, form, index, onClose }) {
      const ctx = dynamicEnumArgMap[config.name as keyof typeof dynamicEnumArgMap];
      const { data, loading } = config.useData(ctx);

      const field = useField({ form, name: `config[${index}]` as const });

      const operator = useStore(field.store, (state) => state.value.operator);

      const multiple = operator === EnumOperators.IN;

      return (
        <form.AppField name={`config[${index}].value` as const}>
          {(field) => (
            <field.MaterialAutocompleteField
              disablePortal
              onClose={onClose}
              options={data}
              multiple={multiple}
              limitTags={1}
              loading={loading}
              size="small"
              sx={{
                width: multiple ? "max-content" : undefined,
                minWidth: 200,
                "& .MuiAutocomplete-input": {
                  width: multiple ? undefined : "max-content !important",
                },
                "& .MuiAutocomplete-inputRoot": {
                  borderRadius: 0,
                  "& fieldset": {
                    borderInlineWidth: 0,
                  },
                },
              }}
              renderInput={(params) => <TextField {...params} variant="filled" label="Value" />}
            />
          )}
        </form.AppField>
      );
    },
  });

  const getAvailableOperators = (metrics: { name: string; operator: string }[], key: string): Operator[] => {
    if (!key || key === "") return [];

    const field = fields.find((field) => field.name === key);
    if (!field) return [];

    const used = metrics.filter((m) => m.name === key && m.operator !== "");
    if (!used.length) return field.operators;

    return field.operators
      .filter((operator) => !used.some((m) => m.operator === operator))
      .filter((operator) => used.every((m) => m.operator && canBeCombinedWith(operator, m.operator as Operator)));
  };

  return { FiltersRow, FilterItem, ValueInput, DynamicEnumInput };
}
