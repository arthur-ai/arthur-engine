import { DatePicker, DatePickerProps } from "@mui/x-date-pickers/DatePicker";
import { Dayjs } from "dayjs";

import { useFieldContext } from "@/components/traces/components/filtering/hooks/form-context";

export const DatePickerField = ({
  value,
  onChange,
  ...props
}: Omit<DatePickerProps, "value" | "onChange"> & {
  value?: Dayjs | null;
  onChange?: (value: Dayjs | null) => void;
}) => {
  const field = useFieldContext<string>();

  return (
    <DatePicker
      {...props}
      value={value ?? null}
      onChange={(newValue) => {
        // Store as ISO string for serialization
        field.handleChange(newValue?.toISOString() ?? "");
        onChange?.(newValue);
      }}
      slotProps={{
        ...props.slotProps,
        textField: {
          size: "small",
          onBlur: () => field.handleBlur(),
          ...props.slotProps?.textField,
        },
      }}
    />
  );
};
