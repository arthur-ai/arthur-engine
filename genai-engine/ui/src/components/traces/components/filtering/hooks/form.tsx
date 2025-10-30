import { createFormHook } from "@tanstack/react-form";

import { formContext, fieldContext } from "./form-context";

import { NumberField } from "@/components/common/form/NumberField";
import { SelectField } from "@/components/common/form/SelectField";
import { ComboboxField } from "@/components/common/form/ComboboxField";

export const { useAppForm, withFieldGroup, withForm } = createFormHook({
  fieldComponents: {
    SelectField: SelectField.Root,
    ComboboxField: ComboboxField.Root,
    NumberField: NumberField.Root,
  },
  formComponents: {},
  formContext,
  fieldContext,
});
