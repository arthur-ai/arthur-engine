import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Popover } from "@base-ui/react/popover";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowRightIcon from "@mui/icons-material/ArrowRight";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { Breadcrumbs, Button, IconButton, List, ListItemButton, Paper, Stack, TextField, Typography } from "@mui/material";
import { useField, useStore } from "@tanstack/react-form";
import { useMemo, useState } from "react";

import { getSpanInput, getSpanModel, getSpanOutput, getSpanType } from "../../utils/spans";
import { withForm } from "../filtering/hooks/form";

import { addToDatasetFormOptions } from "./form/shared";
import { useSpanSelector } from "./hooks/useSpanSelector";

import { TypeChip } from "@/components/common/span/TypeChip";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { truncateText } from "@/utils/formatters";

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
        backgroundColor: "action.hover",
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

const MAX_PREVIEW_LENGTH = 80;

function spanMatchesSearch(span: NestedSpanWithMetricsResponse, query: string): boolean {
  const q = query.toLowerCase();

  if (span.span_name?.toLowerCase().includes(q)) return true;
  if (span.span_id.toLowerCase().includes(q)) return true;

  const kind = getSpanType(span);
  if (kind?.toLowerCase().includes(q)) return true;

  const model = getSpanModel(span);
  if (model?.toLowerCase().includes(q)) return true;

  const input = getSpanInput(span);
  if (input?.toLowerCase().includes(q)) return true;

  const output = getSpanOutput(span);
  if (output?.toLowerCase().includes(q)) return true;

  return false;
}

const SpanList = ({ spans, onSelectSpan }: SpanListProps) => {
  const [search, setSearch] = useState("");

  const filteredSpans = useMemo(() => {
    if (!search.trim()) return spans;
    return spans.filter((span) => spanMatchesSearch(span, search));
  }, [spans, search]);

  return (
    <Stack className="overflow-auto max-h-[50vh]" sx={{ p: 1 }}>
      <TextField
        size="small"
        label="Search by name, type, model, or content"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ m: 1 }}
      />
      <List dense>
        {filteredSpans.map((span) => {
          const kind = getSpanType(span) ?? OpenInferenceSpanKind.AGENT;
          const model = getSpanModel(span);
          const input = getSpanInput(span);
          const output = getSpanOutput(span);
          const contentPreview = input ? truncateText(input, MAX_PREVIEW_LENGTH) : output ? truncateText(output, MAX_PREVIEW_LENGTH) : null;

          return (
            <ListItemButton key={span.id} onClick={() => onSelectSpan(span.span_id)} sx={{ ...listButtonSx, py: 1 }}>
              <Stack direction="row" alignItems="flex-start" gap={1} width="100%">
                <TypeChip type={kind} />
                <Stack flex={1} minWidth={0}>
                  <Typography variant="body2" fontWeight={500}>
                    {span.span_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {kind}
                    {model ? ` · ${model}` : ""}
                  </Typography>
                  {contentPreview && (
                    <Typography variant="caption" color="text.disabled" noWrap>
                      {contentPreview}
                    </Typography>
                  )}
                </Stack>
              </Stack>
            </ListItemButton>
          );
        })}
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
