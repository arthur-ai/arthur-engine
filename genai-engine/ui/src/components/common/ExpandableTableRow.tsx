import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Collapse, IconButton, TableCell, TableRow } from "@mui/material";
import { ReactNode, useState } from "react";

/**
 * A table row with an expandable full-width detail panel. Give the parent `<Table>`
 * `sx={{ tableLayout: "fixed" }}` and explicit header-cell widths — with automatic
 * table layout the detail panel's colSpan cell shifts the column widths on expand.
 */
type Props = {
  /** Total number of columns the detail area spans, including the expander column. */
  colSpan: number;
  /** Content rendered inside the expanded detail area. */
  detail: ReactNode;
  /** Hides the expand arrow for rows that have no detail content. */
  expandDisabled?: boolean;
  /** The row's visible cells. Callers must also add a leading empty header cell for the expander column. */
  children: ReactNode;
};

export const ExpandableTableRow = ({ colSpan, detail, expandDisabled = false, children }: Props) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <TableRow sx={{ "& > td": { borderBottom: "unset" } }}>
        <TableCell padding="checkbox">
          {!expandDisabled && (
            <IconButton
              size="small"
              aria-label={expanded ? "Collapse row" : "Expand row"}
              aria-expanded={expanded}
              onClick={() => setExpanded((previous) => !previous)}
            >
              <KeyboardArrowRightIcon
                fontSize="small"
                sx={{ transform: expanded ? "rotate(90deg)" : "none", transition: (theme) => theme.transitions.create("transform") }}
              />
            </IconButton>
          )}
        </TableCell>
        {children}
      </TableRow>
      <TableRow>
        <TableCell colSpan={colSpan} sx={{ py: 0 }}>
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            <Box sx={{ py: 1.5 }}>{detail}</Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};
