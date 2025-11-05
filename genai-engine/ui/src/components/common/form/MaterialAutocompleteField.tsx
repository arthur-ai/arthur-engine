import { useFieldContext } from "@/components/traces/components/filtering/hooks/form-context";
import Autocomplete, { AutocompleteProps } from "@mui/material/Autocomplete";

export const MaterialAutocompleteField = <
  const Value,
  Multiple extends boolean,
  DisableClearable extends boolean = false,
  FreeSolo extends boolean = false
>({
  value,
  onBlur,
  onChange,
  multiple = false as Multiple,
  ...props
}: AutocompleteProps<Value, Multiple, DisableClearable, FreeSolo>) => {
  const field = useFieldContext<typeof value>();

  return (
    <Autocomplete
      {...props}
      multiple={multiple}
      value={field.state.value}
      onChange={(event, value, ...rest) => {
        field.handleChange(value);
        onChange?.(event, value, ...rest);
      }}
      onBlur={(event) => {
        field.handleBlur();
        onBlur?.(event);
      }}
    />
  );
};
