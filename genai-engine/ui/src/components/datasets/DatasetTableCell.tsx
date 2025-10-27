import { TableCell, Tooltip } from "@mui/material";
import React from "react";

import { CELL_TRUNCATION_LENGTH } from "@/constants/datasetConstants";
import { formatCellValue, formatFullValue } from "@/utils/datasetFormatters";

interface DatasetTableCellProps {
  value: unknown;
  maxLength?: number;
}

export const DatasetTableCell: React.FC<DatasetTableCellProps> = ({
  value,
  maxLength = CELL_TRUNCATION_LENGTH,
}) => {
  const displayValue = formatCellValue(value, maxLength);
  const fullValue = formatFullValue(value);

  return (
    <TableCell>
      {displayValue.length > maxLength ? (
        <Tooltip title={fullValue} arrow>
          <span>{displayValue}</span>
        </Tooltip>
      ) : (
        displayValue
      )}
    </TableCell>
  );
};
