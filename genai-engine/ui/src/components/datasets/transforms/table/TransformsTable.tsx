import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Box,
  Tooltip,
  TableSortLabel,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { TransformsTableProps } from "../types";

export const TransformsTable: React.FC<TransformsTableProps> = ({
  transforms,
  sortColumn,
  sortDirection,
  onSort,
  onView,
  onEdit,
  onDelete,
}) => {
  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const handleSort = (column: string) => {
    onSort(column);
  };

  return (
    <TableContainer>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "name"}
                direction={sortColumn === "name" ? sortDirection : "asc"}
                onClick={() => handleSort("name")}
              >
                Name
              </TableSortLabel>
            </TableCell>
            <TableCell>Description</TableCell>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "created_at"}
                direction={sortColumn === "created_at" ? sortDirection : "asc"}
                onClick={() => handleSort("created_at")}
              >
                Created At
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "updated_at"}
                direction={sortColumn === "updated_at" ? sortDirection : "asc"}
                onClick={() => handleSort("updated_at")}
              >
                Updated At
              </TableSortLabel>
            </TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {transforms.map((transform) => (
            <TableRow
              key={transform.id}
              hover
              onClick={() => onView(transform)}
              sx={{
                cursor: "pointer",
                "& .action-buttons": {
                  visibility: "visible",
                },
              }}
            >
              <TableCell>{transform.name}</TableCell>
              <TableCell>
                <Box
                  sx={{
                    maxWidth: 300,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {transform.description || <em style={{ color: "#999" }}>No description</em>}
                </Box>
              </TableCell>
              <TableCell>{formatDate(transform.created_at)}</TableCell>
              <TableCell>{formatDate(transform.updated_at)}</TableCell>
              <TableCell align="center">
                <Box
                  className="action-buttons"
                  sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => onEdit(transform)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" onClick={() => onDelete(transform.id)} color="error">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default TransformsTable;
