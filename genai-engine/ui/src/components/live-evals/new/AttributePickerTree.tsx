import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Box, Button, Collapse, IconButton, Stack, Tooltip, Typography } from "@mui/material";
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
            Click any key to select it as the attribute path
          </Typography>
        </Stack>
        <Button size="small" variant="outlined" startIcon={<CloseIcon />} onClick={onCancel}>
          Cancel
        </Button>
      </Stack>
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          px: 2,
          py: 1,
          fontFamily: "monospace",
          fontSize: "0.8rem",
        }}
      >
        <JsonNode data={rawData} path="" selectedPath={selectedPath} onSelectPath={onSelectPath} level={0} />
      </Box>
    </Stack>
  );
};

type JsonNodeProps = {
  data: unknown;
  path: string;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  level: number;
  label?: string;
  isLast?: boolean;
};

const JsonNode = ({ data, path, selectedPath, onSelectPath, level, label, isLast = true }: JsonNodeProps) => {
  const [open, setOpen] = useState(true);
  const isSelected = path === selectedPath && path !== "";
  const indent = level * 16;

  if (data === null || data === undefined) {
    return (
      <ClickableKey
        label={label}
        path={path}
        isSelected={isSelected}
        onSelect={onSelectPath}
        indent={indent}
        valuePreview={<JsonValue value="null" />}
        comma={!isLast}
      />
    );
  }

  if (typeof data === "object" && !Array.isArray(data)) {
    const entries = Object.entries(data as Record<string, unknown>);
    if (entries.length === 0) {
      return (
        <ClickableKey
          label={label}
          path={path}
          isSelected={isSelected}
          onSelect={onSelectPath}
          indent={indent}
          valuePreview={<span>{"{}"}</span>}
          comma={!isLast}
        />
      );
    }

    return (
      <Fragment>
        <Stack
          direction="row"
          alignItems="center"
          sx={{
            pl: `${indent}px`,
            minHeight: 24,
            ...(isSelected && {
              backgroundColor: "primary.50",
              borderLeft: 2,
              borderColor: "primary.main",
            }),
          }}
        >
          <IconButton size="small" onClick={() => setOpen(!open)} sx={{ p: 0, mr: 0.5 }}>
            {open ? <ExpandMoreIcon sx={{ fontSize: 16 }} /> : <ChevronRightIcon sx={{ fontSize: 16 }} />}
          </IconButton>
          {label !== undefined && path !== "" ? (
            <Tooltip title={`Select "${path}"`} placement="right">
              <Box
                component="span"
                onClick={() => onSelectPath(path)}
                sx={{
                  cursor: "pointer",
                  "&:hover": { backgroundColor: "action.hover", borderRadius: 0.5 },
                  px: 0.5,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                <span style={{ color: "var(--mui-palette-info-main)" }}>&quot;{label}&quot;</span>
                <span>: {"{"}</span>
                {isSelected && <CheckCircleIcon sx={{ fontSize: 14 }} color="primary" />}
              </Box>
            </Tooltip>
          ) : (
            <span>{"{"}</span>
          )}
        </Stack>
        <Collapse in={open} timeout="auto" unmountOnExit>
          {entries.map(([key, value], idx) => {
            const childPath = path ? `${path}.${key}` : key;
            return (
              <JsonNode
                key={key}
                data={value}
                path={childPath}
                selectedPath={selectedPath}
                onSelectPath={onSelectPath}
                level={level + 1}
                label={key}
                isLast={idx === entries.length - 1}
              />
            );
          })}
        </Collapse>
        <Box sx={{ pl: `${indent}px`, minHeight: 24, display: "flex", alignItems: "center" }}>
          <Box sx={{ pl: 3 }}>
            {"}"}
            {!isLast && ","}
          </Box>
        </Box>
      </Fragment>
    );
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <ClickableKey
          label={label}
          path={path}
          isSelected={isSelected}
          onSelect={onSelectPath}
          indent={indent}
          valuePreview={<span>[]</span>}
          comma={!isLast}
        />
      );
    }

    return (
      <Fragment>
        <Stack
          direction="row"
          alignItems="center"
          sx={{
            pl: `${indent}px`,
            minHeight: 24,
            ...(isSelected && {
              backgroundColor: "primary.50",
              borderLeft: 2,
              borderColor: "primary.main",
            }),
          }}
        >
          <IconButton size="small" onClick={() => setOpen(!open)} sx={{ p: 0, mr: 0.5 }}>
            {open ? <ExpandMoreIcon sx={{ fontSize: 16 }} /> : <ChevronRightIcon sx={{ fontSize: 16 }} />}
          </IconButton>
          {label !== undefined && path !== "" ? (
            <Tooltip title={`Select "${path}"`} placement="right">
              <Box
                component="span"
                onClick={() => onSelectPath(path)}
                sx={{
                  cursor: "pointer",
                  "&:hover": { backgroundColor: "action.hover", borderRadius: 0.5 },
                  px: 0.5,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                <span style={{ color: "var(--mui-palette-info-main)" }}>&quot;{label}&quot;</span>
                <span>
                  : [{" "}
                  <Typography component="span" variant="caption" color="text.secondary">
                    {data.length} items
                  </Typography>
                </span>
                {isSelected && <CheckCircleIcon sx={{ fontSize: 14 }} color="primary" />}
              </Box>
            </Tooltip>
          ) : (
            <span>[</span>
          )}
        </Stack>
        <Collapse in={open} timeout="auto" unmountOnExit>
          {data.map((item, index) => {
            const childPath = `${path}[${index}]`;
            return (
              <JsonNode
                key={index}
                data={item}
                path={childPath}
                selectedPath={selectedPath}
                onSelectPath={onSelectPath}
                level={level + 1}
                label={String(index)}
                isLast={index === data.length - 1}
              />
            );
          })}
        </Collapse>
        <Box sx={{ pl: `${indent}px`, minHeight: 24, display: "flex", alignItems: "center" }}>
          <Box sx={{ pl: 3 }}>]{!isLast && ","}</Box>
        </Box>
      </Fragment>
    );
  }

  // Primitive value
  const valueStr = typeof data === "string" ? `"${data}"` : String(data);

  return (
    <ClickableKey
      label={label}
      path={path}
      isSelected={isSelected}
      onSelect={onSelectPath}
      indent={indent}
      valuePreview={<JsonValue value={valueStr} type={typeof data} />}
      comma={!isLast}
    />
  );
};

type ClickableKeyProps = {
  label?: string;
  path: string;
  isSelected: boolean;
  onSelect: (path: string) => void;
  indent: number;
  valuePreview: React.ReactNode;
  comma: boolean;
};

const ClickableKey = ({ label, path, isSelected, onSelect, indent, valuePreview, comma }: ClickableKeyProps) => {
  return (
    <Stack
      direction="row"
      alignItems="baseline"
      sx={{
        pl: `${indent + 24}px`,
        minHeight: 24,
        ...(isSelected && {
          backgroundColor: "primary.50",
          borderLeft: 2,
          borderColor: "primary.main",
        }),
      }}
    >
      {label !== undefined && path !== "" ? (
        <Tooltip title={`Select "${path}"`} placement="right">
          <Box
            component="span"
            onClick={() => onSelect(path)}
            sx={{
              cursor: "pointer",
              "&:hover": { backgroundColor: "action.hover", borderRadius: 0.5 },
              px: 0.5,
              display: "inline-flex",
              alignItems: "center",
              gap: 0.5,
            }}
          >
            <span style={{ color: "var(--mui-palette-info-main)" }}>&quot;{label}&quot;</span>
            <span>: </span>
            {valuePreview}
            {isSelected && <CheckCircleIcon sx={{ fontSize: 14 }} color="primary" />}
          </Box>
        </Tooltip>
      ) : (
        <span>
          {valuePreview}
          {comma && ","}
        </span>
      )}
      {label !== undefined && comma && <span>,</span>}
    </Stack>
  );
};

const JsonValue = ({ value, type }: { value: string; type?: string }) => {
  const truncated = value.length > 120 ? value.slice(0, 120) + '..."' : value;

  let color = "text.primary";
  if (type === "string") color = "success.main";
  else if (type === "number") color = "warning.main";
  else if (type === "boolean") color = "info.main";
  else if (value === "null") color = "text.secondary";

  return (
    <Typography component="span" sx={{ color, fontFamily: "monospace", fontSize: "0.8rem", wordBreak: "break-all" }}>
      {truncated}
    </Typography>
  );
};
