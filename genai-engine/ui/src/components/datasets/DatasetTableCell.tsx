import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { Box, IconButton, TableCell, Tooltip } from "@mui/material";
import React, { useState } from "react";

import { CellContentModal } from "./CellContentModal";

import { CELL_TRUNCATION_LENGTH } from "@/constants/datasetConstants";
import { formatCellValue, formatFullValue } from "@/utils/datasetFormatters";

interface DatasetTableCellProps {
  value: unknown;
  columnName: string;
  maxLength?: number;
}

export const DatasetTableCell: React.FC<DatasetTableCellProps> = ({
  value,
  columnName,
  maxLength = CELL_TRUNCATION_LENGTH,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const displayValue = formatCellValue(value, maxLength);
  const fullValue = formatFullValue(value);
  const isTruncated = String(value || "").length > maxLength;

  const handleOpenModal = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsModalOpen(true);
  };

  return (
    <>
      <TableCell>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.25,
            cursor: isTruncated ? "pointer" : "default",
          }}
          onClick={isTruncated ? handleOpenModal : undefined}
        >
          {isTruncated ? (
            <>
              <Tooltip title={fullValue} arrow placement="top">
                <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                  {displayValue}
                </span>
              </Tooltip>
              <IconButton
                size="small"
                sx={{
                  opacity: 0.5,
                  "&:hover": { opacity: 1 },
                  padding: 0.25,
                  flexShrink: 0,
                }}
                onClick={handleOpenModal}
                title="View full content"
              >
                <OpenInFullIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </>
          ) : (
            displayValue
          )}
        </Box>
      </TableCell>

      <CellContentModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        columnName={columnName}
        value={value}
      />
    </>
  );
};
