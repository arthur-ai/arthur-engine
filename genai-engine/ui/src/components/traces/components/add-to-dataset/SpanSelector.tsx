import { Popover } from "@base-ui-components/react/popover";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowRightIcon from "@mui/icons-material/ArrowRight";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { Breadcrumbs, Button, IconButton, List, ListItemButton, ListItemText, Paper, Stack, TextField, Typography } from "@mui/material";
import { useField, useStore } from "@tanstack/react-form";
import { useMemo, useState } from "react";

import { withForm } from "../filtering/hooks/form";

import { addToDatasetFormOptions } from "./form/shared";
import { useSpanSelector } from "./hooks/useSpanSelector";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

const listButtonSx = {
  justifyContent: "flex-start",
  textAlign: "left",
  textTransform: "none",
  fontSize: 14,
  fontWeight: 400,
} as const;

export const SpanSelector = withForm({
  ...addToDatasetFormOptions,
  props: {} as {
    spans: NestedSpanWithMetricsResponse[];
    container: HTMLDivElement;
    index: number;
    name: string;
  },
  render: function Render({ form, spans, container, index, name }) {
    const field = useField({ form, name: `columns[${index}]` as const });
    const path = useStore(field.store, (state) => state.value?.path);

    const {
      selectedSpan,
      navigationPath,
      availableAttributes,
      selectedAttribute,
      getAttributeValue,
      handleGoBack,
      handleSelectValue,
      handleSelectSpan,
      handleNavigateToAttribute,
    } = useSpanSelector({
      spans,
      path,
      name,
      onFieldChange: field.handleChange,
    });

    return (
      <Popover.Root>
        <Popover.Trigger
          render={
            <Button
              variant="outlined"
              color="primary"
              sx={{ width: "100%", textTransform: "none" }}
              size="medium"
              endIcon={<KeyboardArrowDownIcon sx={{ fontSize: 16 }} />}
            />
          }
        >
          {path || "Select span and key"}
        </Popover.Trigger>
        <Popover.Portal container={container}>
          <Popover.Positioner sideOffset={8} className="z-50">
            <Popover.Popup render={<Paper />} className="min-w-(--anchor-width)">
              <NavigationHeader selectedSpan={selectedSpan} navigationPath={navigationPath} onGoBack={handleGoBack} />

              {!selectedSpan ? (
                <SpanList spans={spans} onSelectSpan={handleSelectSpan} />
              ) : (
                <AttributeList
                  attributes={availableAttributes}
                  getAttributeValue={getAttributeValue}
                  onSelectValue={handleSelectValue}
                  onNavigateToAttribute={handleNavigateToAttribute}
                  selectedAttribute={selectedAttribute}
                />
              )}
            </Popover.Popup>
          </Popover.Positioner>
        </Popover.Portal>
      </Popover.Root>
    );
  },
});

type NavigationHeaderProps = {
  selectedSpan: NestedSpanWithMetricsResponse | undefined;
  navigationPath: string;
  onGoBack: () => void;
};

const NavigationHeader = ({ selectedSpan, navigationPath, onGoBack }: NavigationHeaderProps) => {
  return (
    <Stack
      direction="row"
      alignItems="center"
      justifyContent="flex-start"
      gap={1}
      sx={{
        borderBottom: "1px solid",
        borderColor: "divider",
        p: 1,
        backgroundColor: "grey.100",
      }}
    >
      <IconButton size="small" onClick={onGoBack}>
        <ArrowBackIcon sx={{ fontSize: 16 }} />
      </IconButton>
      <Breadcrumbs>
        <Popover.Title render={<Typography variant="body2" color="primary" />}>{selectedSpan?.span_name}</Popover.Title>
        {navigationPath && (
          <Typography variant="body2" color="primary">
            {navigationPath}
          </Typography>
        )}
      </Breadcrumbs>
    </Stack>
  );
};

type SpanListProps = {
  spans: NestedSpanWithMetricsResponse[];
  onSelectSpan: (spanId: string) => void;
};

const SpanList = ({ spans, onSelectSpan }: SpanListProps) => {
  const [search, setSearch] = useState("");

  const filteredSpans = useMemo(() => {
    return spans.filter((span) => (span.span_name?.toLowerCase().includes(search.toLowerCase()) || span.span_id.includes(search)) ?? false);
  }, [spans, search]);

  return (
    <Stack className="overflow-auto max-h-[50vh]" sx={{ p: 1 }}>
      <TextField size="small" label="Search for a span" value={search} onChange={(e) => setSearch(e.target.value)} sx={{ m: 1 }} />
      <List dense>
        {filteredSpans.map((span) => (
          <ListItemButton key={span.id} onClick={() => onSelectSpan(span.span_id)} sx={listButtonSx}>
            <ListItemText primary={span.span_name} secondary={span.span_id} />
          </ListItemButton>
        ))}
      </List>
    </Stack>
  );
};

type AttributeListProps = {
  attributes: string[];
  getAttributeValue: (key: string) => unknown;
  onSelectValue: (key: string) => void;
  onNavigateToAttribute: (e: React.MouseEvent, key: string) => void;
  selectedAttribute: string | null;
};

const AttributeList = ({ attributes, getAttributeValue, onSelectValue, onNavigateToAttribute, selectedAttribute }: AttributeListProps) => {
  return (
    <Stack className="overflow-auto max-h-[50vh]" sx={{ p: 1 }}>
      {attributes.map((attribute) => {
        const value = getAttributeValue(attribute);
        const isObject = typeof value === "object" && value !== null;
        const isSelected = attribute === selectedAttribute;

        return (
          <Button
            key={attribute}
            variant="text"
            color="primary"
            onClick={() => onSelectValue(attribute)}
            sx={{
              ...listButtonSx,
              backgroundColor: isSelected ? "action.selected" : "transparent",
              "&:hover": {
                backgroundColor: isSelected ? "action.selected" : "action.hover",
              },
            }}
          >
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1} width="100%" px={1}>
              <Stack>
                <Typography variant="body2" color="text.primary">
                  {attribute}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {typeof value}
                </Typography>
              </Stack>
              {isObject && (
                <IconButton size="small" onClick={(e) => onNavigateToAttribute(e, attribute)}>
                  <ArrowRightIcon />
                </IconButton>
              )}
            </Stack>
          </Button>
        );
      })}
    </Stack>
  );
};
