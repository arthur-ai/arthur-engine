import { VariableChip } from "@arthur/shared-components";
import { withForm } from "@arthur/shared-components";
import { Box, Divider, Stack, TextField } from "@mui/material";
import { Paper, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect } from "react";

import { newAgentExperimentFormOpts } from "../form";

import { TemplateVariableMappingInput } from "@/lib/api-client/api-client";

export const RequestTimeMapper = withForm({
  ...newAgentExperimentFormOpts,
  render: function Render({ form }) {
    const templateVariableMapping = useStore(form.store, (state) =>
      state.values.templateVariableMapping.filter(
        (item): item is TemplateVariableMappingInput & { source: { type: "request_time_parameter" } } => item.source.type === "request_time_parameter"
      )
    );

    useEffect(() => {
      form.setFieldValue(
        "requestTimeParameters",
        templateVariableMapping.map((item) => ({ name: item.variable_name, value: "" }))
      );
    }, [templateVariableMapping, form]);

    const ready = templateVariableMapping.length > 0;

    return (
      <Stack component={Paper} variant="outlined" p={2} sx={{ opacity: ready ? 1 : 0.5, pointerEvents: ready ? "auto" : "none" }}>
        <Stack>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Request Time Parameters
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Map request time parameters to the template variables used in your endpoint configuration. These are not saved in the database, they are
            passed directly to the execution thread.
          </Typography>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <form.AppField name="requestTimeParameters" mode="array">
          {(field) => (
            <Box className="grid grid-cols-[auto_1fr]" sx={{ rowGap: 2 }}>
              {field.state.value.map((item, index) => (
                <Box key={index} className="grid grid-cols-subgrid col-span-2 items-center" sx={{ gap: 2 }}>
                  <form.Subscribe selector={(state) => state.values.requestTimeParameters[index].name}>
                    {(name) => <VariableChip variable={name} />}
                  </form.Subscribe>
                  <form.AppField name={`requestTimeParameters[${index}].value`}>
                    {(field) => (
                      <TextField size="small" value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} label="Value" />
                    )}
                  </form.AppField>
                </Box>
              ))}
            </Box>
          )}
        </form.AppField>
      </Stack>
    );
  },
});
