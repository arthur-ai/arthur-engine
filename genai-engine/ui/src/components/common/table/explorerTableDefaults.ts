/**
 * Explorer Table Standard — shared MRT configuration
 *
 * All Type 2 (Explorer) tables use these defaults. They enforce the product-wide
 * table UX standard: no hide/show columns, no density toggle, no fullscreen, no
 * column action menus, and a sort icon that behaves like MUI's TableSortLabel
 * (hidden by default, visible on hover, solid on the active sorted column).
 *
 * Usage:
 *   const table = useMaterialReactTable({
 *     ...explorerTableDefaults,
 *     data,
 *     columns,
 *     // table-specific options...
 *   });
 *
 * Override any key as needed for table-specific requirements. muiTablePaperProps
 * and muiTableContainerProps are provided as sensible defaults for full-height
 * embedded tables; override them if the table is used in a different layout context.
 */

import type { MRT_TableOptions } from "material-react-table";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const explorerTableDefaults: Partial<MRT_TableOptions<any>> = {
  // Toolbar — only search and filter toggles; no columns/density/fullscreen buttons
  enableHiding: false,
  enableDensityToggle: false,
  enableFullScreenToggle: false,
  enableColumnActions: false,

  // Sort icon — hidden by default, appears on hover, solid on active sorted column.
  // MRT hardcodes active=true on TableSortLabel so we can't use .Mui-active.
  // Instead we use data-sort which MRT sets only when a column is actually sorted.
  // SyncAltIcon (⇅) is replaced with null so unsorted columns show no icon at all,
  // matching MUI's TableSortLabel default behaviour.
  icons: { SyncAltIcon: () => null },
  muiTableHeadCellProps: {
    sx: {
      "& .MuiTableSortLabel-root": { opacity: "0 !important", transition: "opacity 0.2s" },
      "&:hover .MuiTableSortLabel-root": { opacity: "0.5 !important" },
      "&[data-sort] .MuiTableSortLabel-root": { opacity: "1 !important" },
    },
  },

  // Layout — full-height flex column so the table fills its container
  enableStickyHeader: true,
  muiTablePaperProps: {
    elevation: 1,
    sx: {
      borderRadius: 0,
      display: "flex",
      flexDirection: "column",
      height: "100%",
    },
  },
  muiTableContainerProps: {
    sx: { flex: 1 },
  },
};
