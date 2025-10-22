import { createFormHook } from "@tanstack/react-form";

import { formContext, fieldContext } from "./form-context";

import { NumberField } from "@/components/common/form/NumberField";
import { SelectField } from "@/components/common/form/SelectField";

export const { useAppForm, withFieldGroup, withForm } = createFormHook({
  fieldComponents: {
    SelectField: SelectField.Root,
    NumberField: NumberField.Root,
  },
  formComponents: {},
  formContext,
  fieldContext,
});
