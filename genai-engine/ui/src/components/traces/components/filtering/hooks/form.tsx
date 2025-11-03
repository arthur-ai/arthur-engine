import { createFormHook } from "@tanstack/react-form";

import { formContext, fieldContext } from "./form-context";

import { MaterialAutocompleteField } from "@/components/common/form/MaterialAutocompleteField";
import { NumberField } from "@/components/common/form/NumberField";

export const { useAppForm, withFieldGroup, withForm } = createFormHook({
  fieldComponents: {
    NumberField: NumberField.Root,
    MaterialAutocompleteField,
  },
  formComponents: {},
  formContext,
  fieldContext,
});
