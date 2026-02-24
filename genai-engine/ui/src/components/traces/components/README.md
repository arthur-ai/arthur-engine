# Trace Viewer Components - Migration Status

This directory contains the trace viewer components for `arthur-engine`. As part of the "Primitives and Small Chunks" migration strategy, many presentational components have been extracted to `@arthur/shared-components` while container components remain here.

## Migration Architecture

The trace viewer has been split into two categories:

### Container Components (Remain Here)

These components handle:

- **Data fetching** - Using React Query hooks (`useQuery`, `useSuspenseQuery`)
- **State management** - URL state (`nuqs`), filter store, pagination context
- **Routing** - Navigation via `react-router-dom`
- **App-specific logic** - Analytics tracking, drawer targets, etc.

**Container Components:**

- `TraceDrawerContent.tsx` - Fetches trace data and manages span selection
- `SpanDrawerContent.tsx` - Fetches span data
- `SessionDrawerContent.tsx` - Fetches session data
- `UserDrawerContent.tsx` - Fetches user data
- `TraceLevel.tsx`, `SpanLevel.tsx`, `SessionLevel.tsx` - Table containers that fetch data and create columns
- `TracesView.tsx` - Main container that manages level selection and time range

### Presentational Components (Migrated to shared-components)

These components have been moved to `@arthur/shared-components`:

- `FilterRow` - Pure filter component
- `TracesTable` - Generic table wrapper
- `TracesViewLayout` - Layout component
- `DrawerPagination` - Pagination component
- `SpanTree` - Span tree visualization
- `SpanDetails` - Span details panels
- `TraceDrawerBody`, `SpanDrawerBody`, `SessionDrawerBody`, `UserDrawerBody` - Drawer content components
- Column factories (`createTraceLevelColumns`, etc.)
- Filtering infrastructure (types, fields, rules, utils)

## Current State

### Components Still in This Directory

**Container Components:**

- `TraceDrawerContent.tsx` - Fetches trace data, renders local `TraceDrawerBody` (app-specific AddToDatasetDrawer, FeedbackPanel)
- `SpanDrawerContent.tsx` - Fetches span data, renders `SpanDrawerBody` from `@arthur/shared-components`
- `SessionDrawerContent.tsx` - Fetches session data, renders `SessionDrawerBody` from `@arthur/shared-components`
- `UserDrawerContent.tsx` - Fetches user data, renders local `UserDrawerBody` (uses shared FilterRow, TracesTable, column factories)
- `tables/TraceLevel.tsx`, `SpanLevel.tsx`, `SessionLevel.tsx`, `UserLevel.tsx` - Fetch data, use `TracesTable` and column factories from `@arthur/shared-components`
- `TracesView.tsx` (parent directory) - Uses `TracesViewLayout`, `LEVELS`, `TIME_RANGES` from `@arthur/shared-components`

**App-Specific Components:**

- `add-to-dataset/Drawer.tsx` - Dataset management (not migrated)
- `AnnotationCell/` - Annotation display (may be app-specific)
- `feedback/FeedbackPanel.tsx` - Feedback collection (not migrated)
- Other app-specific utilities and components

**Backward Compatibility:**

- `filtering/filters-row.tsx` - Contains the old `createFilterRow` factory function (kept for backward compatibility)

### Import Strategy

Container components now import presentational components from `@arthur/shared-components`:

1. ✅ **Phase 1 (Complete)**: Extract presentational components to `shared-components`
2. ✅ **Phase 2 (Complete)**: Update imports in this directory to use `@arthur/shared-components`
3. ✅ **Phase 3 (Complete)**: Remove duplicate presentational components from this directory

### Example: How Container Components Work

```tsx
// TraceDrawerContent.tsx (Container - stays here)
export const TraceDrawerContent = ({ traceId }: Props) => {
  // Data fetching
  const { data: trace } = useSuspenseQuery({
    queryKey: ["trace", traceId],
    queryFn: () => apiClient.getTrace(traceId),
  });

  // State management
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const { setDrawerTarget } = useDrawerTarget();
  const navigate = useNavigate();

  // Callbacks
  const handleOpenSpanDrawer = (spanId: string) => {
    setDrawerTarget({ type: "span", id: spanId });
  };

  const handleOpenPlayground = (spanId: string, taskId: string) => {
    navigate(`/tasks/${taskId}/continuous-evals/new?traceId=${traceId}`);
  };

  // Render presentational component
  return (
    <TraceDrawerBody
      trace={trace}
      traceId={traceId}
      selectedSpanId={selectedSpanId}
      onSelectSpan={setSelectedSpanId}
      onRefreshMetrics={handleRefresh}
      onOpenSpanDrawer={handleOpenSpanDrawer}
      onOpenPlayground={handleOpenPlayground}
    />
  );
};
```

## Component Dependencies

Container components in this directory depend on:

- `@tanstack/react-query` - Data fetching
- `nuqs` - URL state management
- `react-router-dom` - Routing
- `@/lib/api-client` - API client
- `@/services/amplitude` - Analytics
- `@arthur/shared-components` - Presentational components (TracesViewLayout, TracesTable, drawer bodies, FilterRow, DrawerPagination, SpanTree, column factories, etc.)

## Migration Notes

### FilterRow Migration

- The old `createFilterRow` factory function remains in `filtering/filters-row.tsx` for backward compatibility
- New code should use the `FilterRow` component from shared-components
- The `FilterRow` component maintains the same initialization behavior (only sets form values when form is empty)

### Column Factories

- Column factories now accept `ColumnDependencies` to inject app-specific components
- This allows the same factories to work across different applications
- Dependencies include: formatters, `Chip`, `DurationCell`, `TraceContentCell`, `AnnotationCell`, etc.

### Drawer Bodies

- All drawer body components are now presentational
- They accept data and callbacks as props
- App-specific components (like `AddToDatasetDrawer`, `FeedbackPanel`) are expected to be provided via props or `ColumnDependencies`

## Next Steps

1. ✅ Presentational components extracted to shared-components
2. ✅ Update imports in container components to use `@arthur/shared-components`
3. ✅ Remove duplicate presentational components from this directory
4. ⏳ Test that functionality remains unchanged after import migration
5. ⏳ Update other applications to use shared-components

## File Structure

```
components/
├── TraceDrawerContent.tsx      # Container - fetches trace, renders local TraceDrawerBody
├── SpanDrawerContent.tsx        # Container - fetches span, renders shared SpanDrawerBody
├── SessionDrawerContent.tsx     # Container - fetches session, renders shared SessionDrawerBody
├── UserDrawerContent.tsx        # Container - fetches user, renders local UserDrawerBody
├── tables/
│   ├── TraceLevel.tsx           # Container - uses shared TracesTable, createTraceLevelColumns
│   ├── SpanLevel.tsx            # Container - uses shared TracesTable, createSpanLevelColumns
│   ├── SessionLevel.tsx         # Container - uses shared TracesTable, createSessionLevelColumns
│   ├── UserLevel.tsx            # Container - uses shared TracesTable, createUserLevelColumns
│   └── components/              # Filter modals, etc.
├── filtering/
│   └── filters-row.tsx          # Backward compatibility - createFilterRow factory
├── drawer/
│   ├── TraceDrawerBody.tsx      # Local - app-specific AddToDatasetDrawer, FeedbackPanel; uses shared DrawerPagination, SpanTree
│   └── UserDrawerBody.tsx       # Local - uses shared FilterRow, TracesTable, column factories, TimeRangeSelect, TracesEmptyState
├── SpanDetails.tsx              # Local - context + Header/Panels/Widgets (shared has SpanDetails wrapper only)
├── TracesTable.tsx              # Local - low-level table render (used by add-to-dataset PreviewTable)
└── [app-specific]               # AddToDatasetDrawer, FeedbackPanel, AnnotationCell, etc.
```

## Important Notes

- **Functionality Preservation**: The migration maintains the same user-facing functionality. Container components continue to work exactly as before, just with presentational components imported from shared-components.

- **Backward Compatibility**: The old `createFilterRow` factory function is kept for any code that hasn't been migrated yet.

- **No Breaking Changes**: The API of container components remains the same. Only internal implementation (imports) will change.

- **Testing**: After updating imports, thorough testing is needed to ensure:
  - Filters work correctly
  - Drawers open and display data
  - Pagination works
  - Span selection works
  - All callbacks fire correctly
