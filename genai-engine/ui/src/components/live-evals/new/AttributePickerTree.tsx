import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Box, Button, Collapse, IconButton, List, ListItemButton, ListItemText, Stack, Typography } from "@mui/material";
import { Fragment, useState } from "react";

type AttributePickerTreeProps = {
  rawData: Record<string, unknown>;
  variableName: string;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  onCancel: () => void;
};

export const AttributePickerTree = ({ rawData, variableName, selectedPath, onSelectPath, onCancel }: AttributePickerTreeProps) => {
  return (
    <Stack sx={{ height: "100%" }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: "divider" }}>
        <Stack>
          <Typography variant="subtitle2" fontWeight={600}>
            Select an attribute for: <b>{variableName}</b>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Click a value to select its path
          </Typography>
        </Stack>
        <Button size="small" variant="outlined" startIcon={<CloseIcon />} onClick={onCancel}>
          Cancel
        </Button>
      </Stack>
      <Box sx={{ flex: 1, overflow: "auto", px: 1, py: 1 }}>
        <List dense disablePadding>
          <TreeNode data={rawData} path="" selectedPath={selectedPath} onSelectPath={onSelectPath} level={0} />
        </List>
      </Box>
    </Stack>
  );
};

type TreeNodeProps = {
  data: unknown;
  path: string;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  level: number;
  label?: string;
};

const TreeNode = ({ data, path, selectedPath, onSelectPath, level, label }: TreeNodeProps) => {
  const [open, setOpen] = useState(level < 2);

  if (data === null || data === undefined) {
    return (
      <LeafNode label={label ?? path} value="null" path={path} selectedPath={selectedPath} onSelectPath={onSelectPath} level={level} />
    );
  }

  if (typeof data === "object" && !Array.isArray(data)) {
    const entries = Object.entries(data as Record<string, unknown>);
    if (entries.length === 0) {
      return (
        <LeafNode label={label ?? path} value="{}" path={path} selectedPath={selectedPath} onSelectPath={onSelectPath} level={level} />
      );
    }

    return (
      <Fragment>
        {label !== undefined && (
          <ListItemButton onClick={() => setOpen(!open)} sx={{ pl: level * 2 + 1, py: 0.25, minHeight: 32 }}>
            <IconButton size="small" sx={{ mr: 0.5, p: 0 }}>
              {open ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
            </IconButton>
            <ListItemText
              primary={label}
              slotProps={{
                primary: { variant: "body2", fontWeight: 600, color: "text.primary", sx: { fontFamily: "monospace", fontSize: "0.8rem" } },
              }}
            />
          </ListItemButton>
        )}
        <Collapse in={label === undefined || open} timeout="auto" unmountOnExit>
          <List dense disablePadding>
            {entries.map(([key, value]) => {
              const childPath = path ? `${path}.${key}` : key;
              return <TreeNode key={key} data={value} path={childPath} selectedPath={selectedPath} onSelectPath={onSelectPath} level={label !== undefined ? level + 1 : level} label={key} />;
            })}
          </List>
        </Collapse>
      </Fragment>
    );
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <LeafNode label={label ?? path} value="[]" path={path} selectedPath={selectedPath} onSelectPath={onSelectPath} level={level} />
      );
    }

    return (
      <Fragment>
        {label !== undefined && (
          <ListItemButton onClick={() => setOpen(!open)} sx={{ pl: level * 2 + 1, py: 0.25, minHeight: 32 }}>
            <IconButton size="small" sx={{ mr: 0.5, p: 0 }}>
              {open ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
            </IconButton>
            <ListItemText
              primary={`${label} [${data.length}]`}
              slotProps={{
                primary: { variant: "body2", fontWeight: 600, color: "text.primary", sx: { fontFamily: "monospace", fontSize: "0.8rem" } },
              }}
            />
          </ListItemButton>
        )}
        <Collapse in={label === undefined || open} timeout="auto" unmountOnExit>
          <List dense disablePadding>
            {data.map((item, index) => {
              const childPath = `${path}[${index}]`;
              return <TreeNode key={index} data={item} path={childPath} selectedPath={selectedPath} onSelectPath={onSelectPath} level={label !== undefined ? level + 1 : level} label={`[${index}]`} />;
            })}
          </List>
        </Collapse>
      </Fragment>
    );
  }

  // Leaf node (string, number, boolean)
  return (
    <LeafNode label={label ?? path} value={String(data)} path={path} selectedPath={selectedPath} onSelectPath={onSelectPath} level={level} />
  );
};

type LeafNodeProps = {
  label: string;
  value: string;
  path: string;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  level: number;
};

const LeafNode = ({ label, value, path, selectedPath, onSelectPath, level }: LeafNodeProps) => {
  const isSelected = path === selectedPath;
  const truncatedValue = value.length > 80 ? value.slice(0, 80) + "..." : value;

  return (
    <ListItemButton
      onClick={() => onSelectPath(path)}
      selected={isSelected}
      sx={{
        pl: level * 2 + 3.5,
        py: 0.25,
        minHeight: 32,
        borderRadius: 0.5,
        ...(isSelected && {
          backgroundColor: "primary.50",
          borderLeft: 2,
          borderColor: "primary.main",
        }),
      }}
    >
      <ListItemText
        primary={
          <Stack direction="row" spacing={1} alignItems="baseline">
            <Typography variant="body2" component="span" sx={{ fontFamily: "monospace", fontSize: "0.8rem", fontWeight: 500 }}>
              {label}
            </Typography>
            <Typography variant="caption" component="span" color="text.secondary" sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} noWrap>
              {truncatedValue}
            </Typography>
          </Stack>
        }
      />
    </ListItemButton>
  );
};
