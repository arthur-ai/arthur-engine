import { useCallback, useMemo, useState } from "react";
import { type Control, Controller, FormProvider, useFieldArray, useForm, useFormContext, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Add, Delete, FilterList } from "@mui/icons-material";
import {
  Autocomplete,
  Badge,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import z from "zod";

import { type EnumField, FIELDS, type FreeSoloField, type NumericField } from "./fields";
import { canBeCombinedWith } from "./rules";
import { useFilterStore, useTracesIds } from "./stores/filter.store";
import { MetricFilterSchema, type Operator, Operators } from "./types";
import { getFieldLabel, getOperatorLabel } from "./utils";

// Constants
const EMPTY_METRIC = { name: "", operator: "", value: "" } as const;
const GRID_COLUMNS = "1fr minmax(120px, max-content) 1fr auto" as const;
const NUMERIC_STEP = 0.01 as const;

const FormSchema = z.object({
  metrics: z.array(MetricFilterSchema),
});

type FormSchema = z.infer<typeof FormSchema>;

type Props = {
  traces: number;
};

export const TracesFilters = ({ traces }: Props) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const setFilters = useFilterStore((state) => state.setFilters);
  const filters = useFilterStore((state) => state.filters);

  const methods = useForm<FormSchema>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      metrics: [],
    },
  });

  const { control } = methods;
  const isFiltering = filters.length > 0;

  const onSubmit = useCallback(
    (data: FormSchema) => {
      setFilters(data.metrics);
      setDialogOpen(false);
    },
    [setFilters]
  );

  return (
    <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
      <Button
        onClick={() => setDialogOpen(true)}
        startIcon={<FilterList />}
        sx={{ backgroundColor: isFiltering ? "primary.selected" : "transparent" }}
      >
        Filters
        <Badge invisible={!isFiltering} variant="dot" color="primary" sx={{ alignSelf: "start", right: -8, top: -6 }} />
      </Button>

      {isFiltering && (
        <Typography variant="body2" color="text.secondary">
          {traces || "No"} traces matching filters
        </Typography>
      )}

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
        aria-labelledby="filters-dialog-title"
        data-testid="traces-filters-dialog"
      >
        <DialogTitle id="filters-dialog-title">Filters</DialogTitle>
        <DialogContent dividers sx={{ p: 0 }}>
          <form onSubmit={methods.handleSubmit(onSubmit)}>
            <FormProvider {...methods}>
              <MetricsFilter control={control} onClearAll={() => methods.resetField("metrics", { defaultValue: [] })} />
            </FormProvider>
          </form>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

const MetricsFilter = ({ control, onClearAll }: { control: Control<FormSchema>; onClearAll: () => void }) => {
  const { formState } = useFormContext<FormSchema>();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "metrics",
  });

  const valid = formState.isValid;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", overflow: "hidden", height: "100%", maxHeight: "60vh" }}>
      {fields.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ px: 4, py: 2 }}>
          No filters added yet...
        </Typography>
      ) : (
        <Box sx={{ minHeight: 0, overflow: "auto", px: 4, py: 2 }}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {fields.map((field, index) => (
              <Box
                key={field.id}
                sx={{
                  display: "grid",
                  gridTemplateColumns: GRID_COLUMNS,
                  alignItems: "center",
                  gap: 2,
                  p: 2,
                  bgcolor: "grey.100",
                  borderRadius: 1,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <MetricField index={index} control={control} />
                <IconButton onClick={() => remove(index)} aria-label={`Remove metric filter ${index + 1}`}>
                  <Delete />
                </IconButton>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      <Box
        sx={{
          display: "flex",
          gap: 2,
          justifyContent: "flex-start",
          borderTop: "1px solid",
          borderColor: "divider",
          py: 2,
          px: 4,
        }}
      >
        <Button variant="outlined" onClick={() => append(EMPTY_METRIC)} startIcon={<Add />} aria-label="Add new metric filter">
          Add Filter
        </Button>
        <Button onClick={onClearAll} aria-label="Remove all metric filters" sx={{ ml: "auto" }}>
          Clear All
        </Button>
        <Button variant="contained" type="submit" disabled={!valid}>
          Apply
        </Button>
      </Box>
    </Box>
  );
};

const MetricField = ({ index, control }: { index: number; control: Control<FormSchema> }) => {
  const { resetField } = useFormContext<FormSchema>();
  const metrics = useWatch({
    control,
    name: "metrics",
    compute: (value) => value.slice(0, index).map((m) => ({ name: m.name || "", operator: m.operator || "" })),
  });

  const tracesIds = useTracesIds();
  const out = useWatch({ control, name: `metrics.${index}` as const });

  const metric = FIELDS.find((field) => field.name === out.name);

  const availableOperators = useMemo(() => getAvailableOperators(metrics, out.name), [metrics, out.name]);

  const input = (() => {
    if (metric?.type === "numeric") return <NumericInput control={control} index={index} />;
    if (metric?.type === "enum") {
      const isMultiple = out.operator === Operators.IN;

      return isMultiple ? <MultipleEnumInput control={control} index={index} /> : <SingleEnumInput control={control} index={index} />;
    }
    // if (metric?.type === "text") return <TextInput control={control} index={index} />;
    if (metric?.type === "free_solo") {
      const isMultiple = out.operator === Operators.IN;

      const Component = isMultiple ? FreeSoloMultipleInput : FreeSoloSingleInput;

      if (metric.name === "trace_ids") return <Component control={control} index={index} options={tracesIds} />;
    }

    return null;
  })();

  return (
    <Box sx={{ display: "grid", gridColumn: "span 3", gridTemplateColumns: "subgrid", alignItems: "stretch", gap: 2, width: "100%" }}>
      <Controller
        control={control}
        name={`metrics.${index}.name` as const}
        rules={{ required: true }}
        render={({ field: { onChange, ...props } }) => (
          <Select
            {...props}
            onChange={(e) => {
              const newValue = e.target.value;
              onChange(newValue);
              // Reset operator and value when field name changes
              resetField(`metrics.${index}.operator`);
              resetField(`metrics.${index}.value`);
            }}
            sx={{ backgroundColor: "white" }}
          >
            {FIELDS.map((option) => (
              <MenuItem key={option.name} value={option.name}>
                {getFieldLabel(option.name)}
              </MenuItem>
            ))}
          </Select>
        )}
      />

      <Controller
        control={control}
        name={`metrics.${index}.operator` as const}
        rules={{
          validate: (value) => {
            if (!out.name || !availableOperators.length) return "Invalid metric or operator";
            if (value && !availableOperators.includes(value)) return "Invalid operator";
            return true;
          },
        }}
        render={({ field: { onChange, ...props }, fieldState: { error } }) => (
          <Select
            {...props}
            onChange={(e) => {
              const newValue = e.target.value;
              onChange(newValue);
              // Reset value when operator changes
              resetField(`metrics.${index}.value`, {
                defaultValue: newValue === Operators.IN ? [] : "",
              });
            }}
            disabled={!out.name || !availableOperators.length}
            error={!!error}
            sx={{ backgroundColor: "white" }}
          >
            {availableOperators.map((option) => (
              <MenuItem key={option} value={option}>
                {getOperatorLabel(option)}
              </MenuItem>
            ))}
          </Select>
        )}
      />

      {out.operator ? input : <TextField disabled placeholder="Value..." sx={{ backgroundColor: "white" }} />}
    </Box>
  );
};

const NumericInput = ({ control, index }: { control: Control<FormSchema>; index: number }) => {
  const { watch } = useFormContext<FormSchema>();

  const name = watch(`metrics.${index}.name`);

  const fieldConfig = FIELDS.find((field) => field.name === name) as NumericField;

  if (!fieldConfig) {
    console.error(`NumericInput: Field config not found for field: ${name}`);
    return <TextField disabled placeholder="Invalid field configuration" sx={{ backgroundColor: "white" }} />;
  }

  return (
    <Controller
      control={control}
      name={`metrics.${index}.value` as const}
      render={({ field: { onChange, ...props } }) => (
        <TextField
          {...props}
          onChange={onChange}
          placeholder="Value..."
          type="number"
          slotProps={{ htmlInput: { min: fieldConfig.min, max: fieldConfig.max, step: NUMERIC_STEP } }}
          sx={{ backgroundColor: "white" }}
        />
      )}
    />
  );
};

const SingleEnumInput = ({ control, index }: { control: Control<FormSchema>; index: number }) => {
  const out = useWatch({ control, name: `metrics.${index}` as const });
  const fieldConfig = FIELDS.find((field) => field.name === out.name) as EnumField;

  if (!fieldConfig) {
    console.error(`SingleEnumInput: Field config not found for field: ${out.name}`);
    return <TextField disabled placeholder="Invalid field configuration" sx={{ backgroundColor: "white" }} />;
  }

  return (
    <Controller
      control={control}
      name={`metrics.${index}.value` as const}
      render={({ field: { onChange, ref, value, ...props } }) => {
        const stringValue = typeof value === "string" ? value : "";
        const customProps = fieldConfig.getAutocompleteProps?.(stringValue) || {};

        return (
          <Autocomplete
            options={fieldConfig.options}
            value={stringValue}
            onChange={(_, newValue) => onChange(newValue || "")}
            renderInput={(params) => <TextField {...params} placeholder="Value..." ref={ref} sx={{ backgroundColor: "white" }} />}
            {...props}
            {...customProps}
          />
        );
      }}
    />
  );
};

const MultipleEnumInput = ({ control, index }: { control: Control<FormSchema>; index: number }) => {
  const out = useWatch({ control, name: `metrics.${index}` as const });
  const fieldConfig = FIELDS.find((field) => field.name === out.name) as EnumField;

  if (!fieldConfig) {
    console.error(`MultipleEnumInput: Field config not found for field: ${out.name}`);
    return <TextField disabled placeholder="Invalid field configuration" sx={{ backgroundColor: "white" }} />;
  }

  return (
    <Controller
      control={control}
      name={`metrics.${index}.value` as const}
      render={({ field: { onChange, ref, value, ...props } }) => {
        const arrayValue = Array.isArray(value) ? value : [];
        const customProps = fieldConfig.getAutocompleteProps?.(arrayValue) || {};

        return (
          <Autocomplete
            options={fieldConfig.options}
            multiple
            value={arrayValue}
            onChange={(_, newValue) => onChange(newValue || [])}
            renderInput={(params) => <TextField {...params} placeholder="Value..." ref={ref} sx={{ backgroundColor: "white" }} />}
            {...props}
            {...customProps}
          />
        );
      }}
    />
  );
};

// const TextInput = ({ control, index }: { control: Control<FormSchema>; index: number }) => {
//   return (
//     <Controller
//       control={control}
//       name={`metrics.${index}.value` as const}
//       render={({ field: { onChange, ...props } }) => (
//         <TextField {...props} placeholder="Value..." onChange={onChange} sx={{ backgroundColor: "white" }} />
//       )}
//     />
//   );
// };

const FreeSoloSingleInput = ({ control, index, options }: { control: Control<FormSchema>; index: number; options: string[] }) => {
  const out = useWatch({ control, name: `metrics.${index}` as const });
  const fieldConfig = FIELDS.find((field) => field.name === out.name) as FreeSoloField;

  if (!fieldConfig) {
    console.error(`FreeSoloSingleInput: Field config not found for field: ${out.name}`);
    return <TextField disabled placeholder="Invalid field configuration" sx={{ backgroundColor: "white" }} />;
  }

  return (
    <Controller
      control={control}
      name={`metrics.${index}.value` as const}
      render={({ field: { onChange, value, ref, ...props } }) => {
        const stringValue = typeof value === "string" ? value : "";
        const customProps = fieldConfig.getAutocompleteProps?.(stringValue) || {};

        return (
          <Autocomplete
            options={options}
            value={stringValue}
            onChange={(_, newValue) => onChange(newValue || "")}
            renderInput={(params) => <TextField {...params} placeholder="Value..." ref={ref} sx={{ backgroundColor: "white" }} />}
            freeSolo
            {...props}
            {...customProps}
          />
        );
      }}
    />
  );
};

const FreeSoloMultipleInput = ({ control, index, options }: { control: Control<FormSchema>; index: number; options: string[] }) => {
  const out = useWatch({ control, name: `metrics.${index}` as const });
  const fieldConfig = FIELDS.find((field) => field.name === out.name) as FreeSoloField;

  if (!fieldConfig) {
    console.error(`FreeSoloMultipleInput: Field config not found for field: ${out.name}`);
    return <TextField disabled placeholder="Invalid field configuration" sx={{ backgroundColor: "white" }} />;
  }

  return (
    <Controller
      control={control}
      name={`metrics.${index}.value` as const}
      render={({ field: { onChange, value, ref, ...props } }) => {
        const arrayValue = Array.isArray(value) ? value : [];
        const customProps = fieldConfig.getAutocompleteProps?.(arrayValue) || {};

        return (
          <Autocomplete
            options={options}
            multiple
            value={arrayValue}
            onChange={(_, newValue) => onChange(newValue || [])}
            renderInput={(params) => <TextField {...params} placeholder="Value..." ref={ref} sx={{ backgroundColor: "white" }} />}
            freeSolo
            {...props}
            {...customProps}
          />
        );
      }}
    />
  );
};

const getAvailableOperators = (metrics: { name: string; operator: string }[], key: string): Operator[] => {
  if (!key || key === "") return [];

  const field = FIELDS.find((field) => field.name === key);
  if (!field) return [];

  const used = metrics.filter((m) => m.name === key && m.operator !== "");
  if (!used.length) return field.operators;

  return field.operators
    .filter((operator) => !used.some((m) => m.operator === operator))
    .filter((operator) => used.every((m) => m.operator && canBeCombinedWith(operator, m.operator as Operator)));
};
