import CloseIcon from "@mui/icons-material/Close";
import { Dialog, DialogTitle, IconButton } from "@mui/material";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { parseAsString, useQueryState } from "nuqs";

import { columns } from "../../data/columns";
import { usePollExperiment } from "../../hooks/usePollExperiment";

import { TestCaseDetails } from "./TestCaseDetails";

import { useMRTPagination } from "@/hooks/useMRTPagination";
import { AgenticTestCase } from "@/lib/api-client/api-client";

const DEFAULT_DATA: AgenticTestCase[] = [];

type Props = {
  experimentId: string;
};

export const TestCases = ({ experimentId }: Props) => {
  const [selectedRowId, setSelectedRowId] = useQueryState("selectedRowId", parseAsString);
  const { pagination, props } = useMRTPagination();

  const {
    data: testCases,
    isLoading,
    isRefetching,
  } = usePollExperiment(experimentId!, { page: pagination.pageIndex, page_size: pagination.pageSize });

  const table = useMaterialReactTable({
    columns,
    data: testCases?.data ?? DEFAULT_DATA,
    ...props,
    state: { pagination, isLoading, showProgressBars: isRefetching },
    rowCount: testCases?.total_count ?? 0,
    pageCount: testCases?.total_pages ?? 0,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        setSelectedRowId(row.original.dataset_row_id, { history: "push" });
      },
    }),
  });

  const selectedRow = testCases?.data.find((row) => row.dataset_row_id === selectedRowId);

  const handleClose = () => setSelectedRowId(null);

  return (
    <>
      <MaterialReactTable table={table} />
      <Dialog open={!!selectedRowId} onClose={handleClose} fullWidth maxWidth="md">
        <DialogTitle className="flex items-center justify-between">
          Test Case Details
          <IconButton onClick={handleClose} size="small" aria-label="close">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        {selectedRow && <TestCaseDetails testCase={selectedRow} />}
      </Dialog>
    </>
  );
};
