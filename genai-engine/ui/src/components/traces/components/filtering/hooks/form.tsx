import { createFormHook } from "@tanstack/react-form";

import { formContext, fieldContext } from "./form-context";

import { DatePickerField } from "@/components/common/form/DatePickerField";
import { MaterialAutocompleteField } from "@/components/common/form/MaterialAutocompleteField";
import { NumberField } from "@/components/common/form/NumberField";

export const { useAppForm, withFieldGroup, withForm } = createFormHook({
  fieldComponents: {
    NumberField: NumberField.Root,
    MaterialAutocompleteField,
    DatePickerField,
  },
  formComponents: {},
  formContext,
  fieldContext,
});
