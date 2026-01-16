# Arthur Engine UI - Cursor Rules

description: Guidelines for the GenAI Engine React UI application
globs: genai-engine/ui/\*_/_

## Overview

This is a React 19 + TypeScript + Vite application for the Arthur Engine GenAI platform.

## Tech Stack

- **React 19** with TypeScript (strict mode)
- **Vite** for build tooling and dev server
- **Tailwind CSS 4** for styling
- **Material-UI (MUI)** and **Base UI** for component library
- **React Router v7** for routing
- **TanStack Query** for data fetching and server state
- **TanStack Form** for form handling
- **TanStack Table** for tables
- **Zod** for validation
- **nuqs** for URL parameter management
- **Framer Motion** for animations
- **Zustand** for client state
- **Yarn 4** for package management

---

## Core React Principles

### You Might Not Need an Effect

Before adding `useEffect`, ask yourself if the logic can be achieved without it:

```typescript
// ❌ BAD: useEffect to compute derived state
const [firstName, setFirstName] = useState("John");
const [lastName, setLastName] = useState("Doe");
const [fullName, setFullName] = useState("");

useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);

// ✅ GOOD: Derive during render
const [firstName, setFirstName] = useState("John");
const [lastName, setLastName] = useState("Doe");
const fullName = `${firstName} ${lastName}`;
```

**Valid useEffect use cases:**

- Synchronizing with external systems (DOM APIs, third-party libraries)
- Setting up subscriptions or event listeners
- Fetching data that cannot use React Query

**Avoid useEffect for:**

- Transforming data for rendering → compute during render
- Handling user events → use event handlers
- Resetting state when props change → use `key` prop
- Updating parent state → lift state up or use callbacks

### Derived State

If a value can be computed from existing state or props, do NOT create additional state:

```typescript
// ❌ BAD: Redundant state
const [items, setItems] = useState<Item[]>([]);
const [filteredItems, setFilteredItems] = useState<Item[]>([]);
const [itemCount, setItemCount] = useState(0);

useEffect(() => {
  setFilteredItems(items.filter((item) => item.active));
}, [items]);

useEffect(() => {
  setItemCount(filteredItems.length);
}, [filteredItems]);

// ✅ GOOD: Derive values
const [items, setItems] = useState<Item[]>([]);
const [filterActive, setFilterActive] = useState(true);

const filteredItems = useMemo(() => items.filter((item) => (filterActive ? item.active : true)), [items, filterActive]);
const itemCount = filteredItems.length;
```

### State Machine Pattern (Excluding Impossible States)

Instead of multiple boolean flags that can conflict, use discriminated unions:

```typescript
// ❌ BAD: Conflicting boolean states
interface DataState {
  isLoading: boolean;
  isError: boolean;
  isSuccess: boolean;
  data: Data | null;
  error: Error | null;
}
// Can have isLoading=true AND isError=true simultaneously!

// ✅ GOOD: Discriminated union (state machine)
type DataState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: Error }
  | { status: "success"; data: Data };

// Usage with pattern matching
function renderContent(state: DataState) {
  switch (state.status) {
    case "idle":
      return <Placeholder />;
    case "loading":
      return <Spinner />;
    case "error":
      return <ErrorDisplay error={state.error} />;
    case "success":
      return <DataDisplay data={state.data} />;
  }
}
```

TanStack Query already uses this pattern - leverage it:

```typescript
const { data, error, status, isPending, isError, isSuccess } = useQuery({...});

// Prefer status checks over multiple boolean checks
if (status === "pending") return <Loading />;
if (status === "error") return <Error error={error} />;
return <Content data={data} />;
```

---

## Type Safety

### Use Backend-Generated Types

The API client is auto-generated from OpenAPI spec. **Always use these types directly:**

```typescript
// ❌ BAD: Manually creating types that mirror backend
interface MyPrompt {
  name: string;
  version: number;
  content: string;
}

// ✅ GOOD: Import from generated client
import { AgenticPrompt, TraceMetadataResponse } from "@/lib/api-client/api-client";
```

**Inferring types from backend types:**

```typescript
import { AgenticPrompt } from "@/lib/api-client/api-client";

// Infer partial types
type PromptFormData = Pick<AgenticPrompt, "name" | "description">;

// Infer from array responses
type TraceItem = TraceMetadataResponse;
```

### TypeScript Rules

- **NEVER use `any`** - use `unknown` and narrow, or create proper types
- Use `interface` for object shapes, `type` for unions/intersections
- Always type function parameters and return values
- Use `React.FC<Props>` for functional components
- Use `ReactNode` for children props

```typescript
// ❌ BAD
const handleData = (data: any) => { ... }

// ✅ GOOD
const handleData = (data: unknown): ProcessedData => {
  if (!isValidData(data)) throw new Error("Invalid data");
  return processData(data);
}
```

---

## Data Fetching with TanStack Query

### Query Patterns

Use the existing `useApiQuery` hook or direct `useQuery`:

```typescript
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";

// Using the typed useApiQuery hook
const { data, isPending, error } = useApiQuery({
  method: "getDatasetApiV2DatasetsDatasetIdGet",
  args: [{ datasetId }],
  enabled: !!datasetId,
});

// Direct useQuery with queryKeys
const { data, isFetching, error } = useQuery({
  queryKey: queryKeys.traces.listPaginated(params),
  queryFn: () => getFilteredTraces(api, params),
  placeholderData: keepPreviousData,
});
```

### Mutation Patterns

Use `useApiMutation` for mutations with automatic cache invalidation:

```typescript
import { useApiMutation } from "@/hooks/useApiMutation";
import { queryKeys } from "@/lib/queryKeys";

const mutation = useApiMutation({
  mutationFn: (variables) => api.api.createDataset(variables),
  invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }],
  onSuccess: (data) => {
    showSnackbar("Created successfully!", "success");
  },
  onError: (error) => {
    showSnackbar(error.message, "error");
  },
});
```

### Query Keys

Always use the centralized `queryKeys` object for consistency:

```typescript
// In @/lib/queryKeys.ts
export const queryKeys = {
  datasets: {
    search: {
      all: () => ["getDatasetsApiV2DatasetsSearchGet"] as const,
      filtered: (filters: Record<string, unknown>) => ["getDatasetsApiV2DatasetsSearchGet", filters] as const,
    },
    detail: (datasetId: string) => ["getDatasetApiV2DatasetsDatasetIdGet", datasetId] as const,
  },
  // ...
} as const;
```

---

## Forms with TanStack Form + Zod

### Form Setup

```typescript
import { useForm } from "@tanstack/react-form";
import { z } from "zod";

// Define schema with Zod
const formSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).optional(),
});

type FormValues = z.infer<typeof formSchema>;

// Use TanStack Form
const form = useForm({
  defaultValues: { name: "", description: "" },
  onSubmit: async ({ value }) => {
    const result = formSchema.safeParse(value);
    if (!result.success) return;
    await mutation.mutateAsync(result.data);
  },
});
```

### Field Rendering with MUI

```tsx
<form.Field
  name="name"
  validators={{
    onChange: ({ value }) => {
      const result = z.string().min(1).safeParse(value);
      return result.success ? undefined : result.error.issues[0].message;
    },
  }}
>
  {(field) => (
    <TextField
      label="Name"
      value={field.state.value}
      onChange={(e) => field.handleChange(e.target.value)}
      onBlur={field.handleBlur}
      error={field.state.meta.errors.length > 0}
      helperText={field.state.meta.errors[0]}
      fullWidth
    />
  )}
</form.Field>
```

---

## Tables with TanStack Table

### Basic Table Setup

```typescript
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  ColumnDef,
  SortingState,
} from "@tanstack/react-table";

const columns: ColumnDef<DataType>[] = [
  {
    header: "Name",
    accessorKey: "name",
  },
  {
    header: "Status",
    accessorFn: (row) => row.status,
    cell: ({ getValue }) => <StatusBadge status={getValue()} />,
  },
];

const [sorting, setSorting] = useState<SortingState>([]);

const table = useReactTable({
  data: data ?? [],
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  state: { sorting },
  onSortingChange: setSorting,
  manualPagination: true,
  rowCount: totalCount,
});
```

---

## URL State with nuqs

### URL Parameter Management

```typescript
import { parseAsString, parseAsStringLiteral, useQueryState, useQueryStates } from "nuqs";

// Single parameter
const [search, setSearch] = useQueryState("search", parseAsString.withDefault(""));

// Multiple parameters with type safety
const TABS = ["overview", "details", "settings"] as const;

const [params, setParams] = useQueryStates({
  tab: parseAsStringLiteral(TABS).withDefault("overview"),
  id: parseAsString,
});

// Serialization for links
import { createSerializer } from "nuqs";
const serialize = createSerializer({
  tab: parseAsStringLiteral(TABS),
  id: parseAsString,
});
const href = serialize({ tab: "details", id: "123" }); // "?tab=details&id=123"
```

---

## Component Guidelines

### Component Structure

- **One component per file** with matching filename
- Use **PascalCase** for component names and files
- Export components as **named exports**
- Use **barrel exports** (index.ts) for clean imports

```typescript
// components/traces/components/TracesTable/index.tsx
export { TracesTable } from "./TracesTable";
export type { TracesTableProps } from "./types";
```

### MUI + Tailwind Styling

- **Use MUI components** as the foundation for UI patterns
- **Use Tailwind utilities** for spacing, layout, and custom styling
- Combine via `className` prop on MUI components

```tsx
<Card className="p-4 mb-6">
  <Typography variant="h6" className="mb-2">
    Title
  </Typography>
  <Box className="flex gap-2">
    <Button variant="contained">Primary</Button>
    <Button variant="outlined">Secondary</Button>
  </Box>
</Card>
```

### Icons

Use MUI icons from `@mui/icons-material`:

```typescript
import { Add, Edit, Delete, Search } from "@mui/icons-material";
```

---

## State Management

### Client State with Zustand

For complex client-side state, use Zustand stores:

```typescript
import { create } from "zustand";

interface FilterState {
  filters: Filter[];
  timeRange: TimeRange;
  actions: {
    setFilters: (filters: Filter[]) => void;
    setTimeRange: (range: TimeRange) => void;
    reset: () => void;
  };
}

export const useFilterStore = create<FilterState>((set) => ({
  filters: [],
  timeRange: defaultTimeRange,
  actions: {
    setFilters: (filters) => set({ filters }),
    setTimeRange: (timeRange) => set({ timeRange }),
    reset: () => set({ filters: [], timeRange: defaultTimeRange }),
  },
}));
```

### React Context

Use Context for:

- Authentication state (AuthContext)
- Task/workspace context (TaskContext)
- Theme configuration

---

## Error Handling

### Query Error States

```tsx
const { data, error, isPending } = useQuery({...});

if (isPending) return <LoadingSpinner />;
if (error) return <Alert severity="error">{error.message}</Alert>;
return <DataDisplay data={data} />;
```

### Error Boundaries

Wrap feature sections with error boundaries:

```tsx
import { ErrorBoundary } from "react-error-boundary";
import { ErrorFallback } from "@/components/common/ErrorFallback";

<ErrorBoundary FallbackComponent={ErrorFallback}>
  <FeatureComponent />
</ErrorBoundary>;
```

---

## File Organization

```
src/
├── components/           # Feature components
│   ├── common/          # Shared UI components
│   ├── traces/          # Traces feature
│   │   ├── components/  # Sub-components
│   │   ├── hooks/       # Feature-specific hooks
│   │   ├── stores/      # Zustand stores
│   │   └── data/        # Column definitions, constants
│   └── datasets/        # Datasets feature
├── contexts/            # React Context providers
├── hooks/               # Shared custom hooks
├── lib/                 # Utilities
│   ├── api-client/      # Auto-generated API client
│   ├── queryClient.ts   # React Query client
│   └── queryKeys.ts     # Centralized query keys
├── schemas/             # Zod schemas
├── services/            # API service functions
├── types/               # Shared TypeScript types
└── utils/               # Utility functions
```

---

## Anti-Patterns to Avoid

1. **Don't use `any`** - use proper types or `unknown`
2. **Don't use `useEffect` for derived state** - compute during render
3. **Don't create conflicting boolean flags** - use discriminated unions
4. **Don't manually create types** that exist in the API client
5. **Don't mutate state directly** - use immutable updates
6. **Don't skip loading/error states** - always handle them
7. **Don't use inline styles** - use Tailwind utilities
8. **Don't hardcode API URLs** - use environment variables
9. **Don't commit console.log statements**
10. **Don't create custom components** when MUI equivalents exist

---

## Commands (Required Before Committing)

Always run `yarn check` after making changes - this runs type-check, lint, and format:check.
CI will block PRs that fail these checks.

```bash
# Run ALL checks (REQUIRED before committing)
yarn check

# Individual commands
yarn dev           # Development server
yarn type-check    # TypeScript checking
yarn lint          # ESLint
yarn format        # Prettier (auto-fix)
yarn format:check  # Prettier (check only)

# Regenerate API client
yarn generate-api
```
