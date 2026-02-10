import { Popover } from "@base-ui/react/popover";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import DataObjectIcon from "@mui/icons-material/DataObject";
import { Button, Chip, List, ListItemButton, ListItemIcon, ListItemText, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useRef, useState } from "react";

import { Column } from "./form/shared";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

type SpanObject = {
  path: string;
  spanId: string;
  spanName: string;
  value: Record<string, unknown>;
  keys: string[];
  matchingKeys: string[];
  matchCount: number;
};

type FillFromObjectButtonProps = {
  spans: NestedSpanWithMetricsResponse[];
  columns: Column[];
  onFillColumns: (updatedColumns: Column[]) => void;
};

function findAllObjects(
  obj: unknown,
  path: string,
  span: NestedSpanWithMetricsResponse,
  columnNamesLower: Set<string>,
  results: SpanObject[],
  maxDepth = 8
): void {
  if (maxDepth <= 0 || typeof obj !== "object" || obj === null || Array.isArray(obj)) {
    return;
  }

  const objRecord = obj as Record<string, unknown>;
  const keys = Object.keys(objRecord);
  if (keys.length === 0) return;

  const matchingKeys = keys.filter((k) => columnNamesLower.has(k.toLowerCase()));

  results.push({
    path,
    spanId: span.span_id,
    spanName: span.span_name ?? "",
    value: objRecord,
    keys,
    matchingKeys,
    matchCount: matchingKeys.length,
  });

  for (const key of keys) {
    const childPath = path ? `${path}.${key}` : key;
    findAllObjects(objRecord[key], childPath, span, columnNamesLower, results, maxDepth - 1);
  }
}

export function FillFromObjectButton({ spans, columns, onFillColumns }: FillFromObjectButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const columnNamesLower = useMemo(() => new Set(columns.map((c) => c.name.toLowerCase())), [columns]);

  const allObjects = useMemo(() => {
    const results: SpanObject[] = [];
    for (const span of spans) {
      if (span.raw_data) {
        findAllObjects(span.raw_data, "", span, columnNamesLower, results);
      }
    }
    return results;
  }, [spans, columnNamesLower]);

  const displayedObjects = useMemo(() => {
    let filtered: SpanObject[];

    if (!search.trim()) {
      filtered = allObjects.filter((o) => o.matchCount > 0);
    } else {
      const q = search.toLowerCase();
      filtered = allObjects.filter((o) => o.path.toLowerCase().includes(q) || o.keys.some((k) => k.toLowerCase().includes(q)));
    }

    return filtered.sort((a, b) => {
      if (a.matchCount !== b.matchCount) return b.matchCount - a.matchCount;
      return a.path.length - b.path.length;
    });
  }, [allObjects, search]);

  const handleSelect = (obj: SpanObject) => {
    const span = spans.find((s) => s.span_id === obj.spanId);
    if (!span) return;

    const keyMap = new Map<string, string>();
    for (const key of obj.keys) {
      keyMap.set(key.toLowerCase(), key);
    }

    const updated = columns.map((col) => {
      const actualKey = keyMap.get(col.name.toLowerCase());
      if (!actualKey) return col;

      const value = obj.value[actualKey];
      const attrPath = obj.path ? `${obj.path}.${actualKey}` : actualKey;

      return {
        ...col,
        value: typeof value === "object" ? JSON.stringify(value) : String(value ?? ""),
        path: `${span.span_name ?? ""}.${attrPath}`,
        span_name: span.span_name ?? "",
        attribute_path: attrPath,
        // avoid stale multi-match UI state
        matchCount: undefined,
        selectedSpanId: undefined,
        allMatches: undefined,
      };
    });

    onFillColumns(updated);
    setOpen(false);
  };

  const getKeysPreview = (obj: SpanObject) => {
    const previewKeys = obj.keys.slice(0, 4);
    const suffix = obj.keys.length > 4 ? ` +${obj.keys.length - 4}` : "";
    return previewKeys.join(", ") + suffix;
  };

  return (
    <div ref={containerRef}>
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Trigger render={<Button variant="outlined" startIcon={<AutoFixHighIcon />} sx={{ textTransform: "none" }} size="small" />}>
          Fill from Object
        </Popover.Trigger>
        <Popover.Portal container={containerRef.current}>
          <Popover.Positioner sideOffset={8} className="z-50">
            <Popover.Popup render={<Paper />} className="min-w-[400px] max-w-[600px]">
              <Stack sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
                <TextField
                  size="small"
                  placeholder="Search attributes..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  fullWidth
                  autoFocus
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                  {search ? "Showing all matching objects" : "Showing objects with column matches"}
                </Typography>
              </Stack>

              <List dense className="overflow-auto max-h-[50vh]">
                {displayedObjects.length === 0 ? (
                  <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: "center" }}>
                    {search ? "No objects found matching your search" : "No objects with matching column names found. Try searching."}
                  </Typography>
                ) : (
                  displayedObjects.map((obj) => {
                    const hasMatches = obj.matchCount > 0;

                    return (
                      <ListItemButton key={`${obj.spanId}-${obj.path}`} onClick={() => handleSelect(obj)}>
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <DataObjectIcon fontSize="small" color={hasMatches ? "primary" : "disabled"} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body2" sx={{ wordBreak: "break-all" }} color={hasMatches ? "text.primary" : "text.secondary"}>
                              {obj.path ? `${obj.spanName}.${obj.path}` : obj.spanName}
                            </Typography>
                          }
                          secondary={
                            <Stack direction="column" gap={0.5} mt={0.5}>
                              <Stack direction="row" gap={0.5} alignItems="center">
                                <Chip
                                  size="small"
                                  label={`${obj.matchCount} match${obj.matchCount !== 1 ? "es" : ""}`}
                                  color={hasMatches ? "success" : "default"}
                                  variant={hasMatches ? "filled" : "outlined"}
                                />
                                {hasMatches && (
                                  <Typography variant="caption" color="text.secondary">
                                    {obj.matchingKeys.slice(0, 3).join(", ")}
                                    {obj.matchingKeys.length > 3 && ` +${obj.matchingKeys.length - 3}`}
                                  </Typography>
                                )}
                              </Stack>
                              {!hasMatches && (
                                <Typography variant="caption" color="text.disabled">
                                  Keys: {getKeysPreview(obj)}
                                </Typography>
                              )}
                            </Stack>
                          }
                        />
                      </ListItemButton>
                    );
                  })
                )}
              </List>
            </Popover.Popup>
          </Popover.Positioner>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
