import { useDatasets } from "@/hooks/useDatasets";
import { useTask } from "@/hooks/useTask";
import {
  Autocomplete,
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { useTrace } from "@/hooks/useTrace";
import { useAppForm } from "../filtering/hooks/form";
import { useStore } from "@tanstack/react-form";
import { DatasetResponse } from "@/lib/api-client/api-client";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { useMemo } from "react";
import { Drawer } from "@/components/common/Drawer";

type Props = {
  traceId: string;
};

export const AddToDatasetDrawer = ({ traceId }: Props) => {
  const form = useAppForm({
    defaultValues: {
      dataset: "",
    },
  });

  const datasetId = useStore(form.store, (state) => state.values.dataset);

  const { task } = useTask();

  const { datasets } = useDatasets(task?.id, {
    page: 0,
    pageSize: 10,
    sortOrder: "asc",
  });

  const { data: trace } = useTrace(traceId);

  const selectedDataset = datasets.find((dataset) => datasetId === dataset.id);

  return (
    <Drawer>
      <Drawer.Trigger render={<Button startIcon={<AddIcon />} />}>
        Add to Dataset
      </Drawer.Trigger>

      <Drawer.Content>
        <Stack
          direction="row"
          spacing={0}
          justifyContent="space-between"
          alignItems="center"
          sx={{
            px: 4,
            py: 2,
            backgroundColor: "grey.100",
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Stack direction="column" spacing={0}>
            <Typography variant="h5" color="text.primary" fontWeight="bold">
              Add to Dataset
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select a span and drill down through its keys to extract data. The
              live preview shows the current value.
            </Typography>
          </Stack>
        </Stack>
        <Stack
          direction="column"
          gap={2}
          sx={{ p: 4, overflow: "auto", flex: 1 }}
          component="form"
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
        >
          <form.Field name="dataset">
            {(field) => (
              <Autocomplete
                options={datasets}
                disablePortal
                renderInput={(params) => (
                  <TextField {...params} label="Select Dataset" />
                )}
                onChange={(event, value) => {
                  field.handleChange(value?.id ?? "");
                }}
                getOptionLabel={(option) => option.name}
              />
            )}
          </form.Field>
          {selectedDataset && <Configurator dataset={selectedDataset} />}
          <form.Subscribe
            selector={(state) => state.values.dataset}
            children={(dataset) => (
              <Box>
                <Typography variant="body1" color="text.primary">
                  {dataset}
                </Typography>
              </Box>
            )}
          />
        </Stack>
      </Drawer.Content>
    </Drawer>
    // <Drawer.Root direction="right">
    //   <Drawer.Trigger asChild>
    //     <Button startIcon={<AddIcon />}>Add to Dataset</Button>
    //   </Drawer.Trigger>
    //   <Drawer.Portal>
    //     <Box
    //       component={Drawer.Overlay}
    //       sx={{
    //         backgroundColor: "oklch(0 0 360 / 0.5)",
    //         position: "fixed",
    //         inset: 0,
    //         zIndex: 10,
    //       }}
    //     />

    //     <Box
    //       component={Drawer.Content}
    //       sx={{
    //         backgroundColor: "background.paper",
    //         position: "fixed",
    //         insetBlock: 0,
    //         right: 0,
    //         zIndex: 11,
    //         width: "90%",
    //         overflow: "hidden",
    //         display: "flex",
    //         flexDirection: "column",
    //       }}
    //     >
    //       <Stack
    //         direction="row"
    //         spacing={0}
    //         justifyContent="space-between"
    //         alignItems="center"
    //         sx={{
    //           px: 4,
    //           py: 2,
    //           backgroundColor: "grey.100",
    //           borderBottom: "1px solid",
    //           borderColor: "divider",
    //         }}
    //       >
    //         <Stack direction="column" spacing={0}>
    //           <Drawer.Title>
    //             <Typography variant="h5" color="text.primary" fontWeight="bold">
    //               Add to Dataset
    //             </Typography>
    //           </Drawer.Title>
    //           <Drawer.Description>
    //             <Typography variant="body2" color="text.secondary">
    //               Select a span and drill down through its keys to extract data.
    //               The live preview shows the current value.
    //             </Typography>
    //           </Drawer.Description>
    //         </Stack>
    //       </Stack>
    //       <Stack
    //         direction="column"
    //         gap={2}
    //         sx={{ p: 4, overflow: "auto", flex: 1 }}
    //         component="form"
    //         onSubmit={(e) => {
    //           e.preventDefault();
    //           e.stopPropagation();
    //           form.handleSubmit();
    //         }}
    //       >
    //         <form.Field name="dataset">
    //           {(field) => (
    //             <Autocomplete
    //               options={datasets}
    //               disablePortal
    //               renderInput={(params) => (
    //                 <TextField {...params} label="Select Dataset" />
    //               )}
    //               onChange={(event, value) => {
    //                 field.handleChange(value?.id ?? "");
    //               }}
    //               getOptionLabel={(option) => option.name}
    //             />
    //           )}
    //         </form.Field>
    //         {selectedDataset && <Configurator dataset={selectedDataset} />}
    //         <form.Subscribe
    //           selector={(state) => state.values.dataset}
    //           children={(dataset) => (
    //             <Box>
    //               <Typography variant="body1" color="text.primary">
    //                 {dataset}
    //               </Typography>
    //             </Box>
    //           )}
    //         />
    //       </Stack>
    //       <Box sx={{ px: 4, py: 2 }}>XD</Box>
    //     </Box>
    //   </Drawer.Portal>
    // </Drawer.Root>
  );
};

const Configurator = ({ dataset }: { dataset: DatasetResponse }) => {
  const { version } = useDatasetVersionData(
    dataset.id,
    dataset.latest_version_number!
  );

  return (
    <div className="grid grid-cols-[1fr_2fr] gap-2">
      {version?.column_names.map((columnName) => (
        <div className="grid grid-cols-subgrid col-span-2">
          <Typography variant="body1" color="text.primary">
            {columnName}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Extracted Value
          </Typography>
        </div>
      ))}
    </div>
  );
};

const PreviewTable = ({ columnNames }: { columnNames: string[] }) => {
  const columns = useMemo(() => {
    return columnNames.map((columnName) => ({}));
  }, [columnNames]);

  return columnNames.join(", ");
};
