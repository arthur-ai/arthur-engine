# GenAI Engine UI - Coding Standards

This document defines the coding standards and patterns for the GenAI Engine frontend (React + TypeScript).

## Technology Stack

- **React** 19.x with functional components
- **TypeScript** 5.x with strict mode
- **Vite** for bundling
- **Tailwind CSS** 4.x + **MUI** 7.x for styling
- **TanStack Query** for server state
- **React Router** 7.x for routing
- **Zod** for runtime validation

---

## Code Formatting & Linting

### Prettier Configuration

```json
{
  "trailingComma": "es5",
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": false,
  "jsxSingleQuote": false,
  "bracketSpacing": true,
  "printWidth": 150
}
```

### ESLint Rules

- Import ordering: `builtin → external → internal → parent → sibling → index`
- Alphabetized imports (case-insensitive)
- Unused variables: allowed only with `_` prefix (e.g., `_unusedVar`)
- Strict TypeScript checks enabled

### Pre-Commit Workflow

```bash
yarn type-check    # TypeScript validation
yarn lint          # ESLint check
yarn format        # Prettier formatting
```

---

## Project Structure

```
src/
├── components/           # Feature-based organization
│   ├── common/          # Reusable UI components
│   └── {feature}/       # Feature-specific components
│       ├── hooks/       # Feature-specific hooks
│       ├── types.ts     # Feature-specific types
│       └── *.tsx        # Feature components
├── contexts/            # React Context providers
├── hooks/               # Shared custom hooks
├── lib/                 # Core utilities
│   ├── api-client/      # AUTO-GENERATED (never edit)
│   ├── api.ts
│   ├── queryClient.ts
│   └── queryKeys.ts
├── schemas/             # Zod validation schemas
├── services/            # Business logic services
├── types/               # Shared TypeScript types
├── utils/               # Helper functions
└── constants/           # Application constants
```

---

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `PromptsManagement.tsx` |
| Component files | Same as component | `PromptsManagement.tsx` |
| Folders | kebab-case | `prompts-management/` |
| Hooks | camelCase with `use` prefix | `usePrompts`, `useApiQuery` |
| Utilities | camelCase | `formatDate`, `cn` |
| Types/Interfaces | PascalCase | `PromptsTableProps` |
| Constants | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |

---

## Component Patterns

### Component Definition

```typescript
interface ComponentNameProps {
  required: string;
  optional?: string;
  children?: React.ReactNode;
}

export const ComponentName: React.FC<ComponentNameProps> = ({
  required,
  optional = "default"
}) => {
  return <div>{required}</div>;
};
```

### Co-location

Keep related code close to where it's used:

```
components/feature-name/
├── FeatureName.tsx           # Main component
├── FeatureNameHeader.tsx     # Sub-components
├── hooks/
│   ├── useFeatureData.ts     # Feature-specific hooks
│   └── useFeatureMutation.ts
├── types.ts                  # Feature-specific types
└── table/
    └── FeatureTable.tsx      # Complex sub-components
```

---

## State Management

### Hierarchy

1. **Server State**: TanStack Query for API data
2. **Global State**: React Context for auth, current task
3. **Local State**: `useState` for component-level state
4. **URL State**: `nuqs` for URL parameters

### Context Pattern

```typescript
const FeatureContext = createContext<FeatureContextType | undefined>(undefined);

export const useFeature = () => {
  const context = useContext(FeatureContext);
  if (context === undefined) {
    throw new Error("useFeature must be used within FeatureProvider");
  }
  return context;
};
```

### Avoid Derived State in useState

```typescript
// BAD - storing derived state
const [filteredItems, setFilteredItems] = useState([]);
useEffect(() => {
  setFilteredItems(items.filter(predicate));
}, [items]);

// GOOD - compute during render
const filteredItems = useMemo(() => items.filter(predicate), [items]);
```

---

## Data Fetching

### Query Keys

Use centralized query key factory:

```typescript
// lib/queryKeys.ts
export const queryKeys = {
  datasets: {
    all: () => ["datasets"] as const,
    detail: (id: string) => ["datasets", id] as const,
    search: {
      all: () => [...queryKeys.datasets.all(), "search"] as const,
    },
  },
};
```

### Custom Query Hook

```typescript
export function useFeatureData(id: string) {
  const api = useApi();

  return useApiQuery({
    method: "getFeatureApiV2FeatureIdGet",
    args: [{ featureId: id }],
    enabled: !!id,
  });
}
```

### Custom Mutation Hook

```typescript
export function useDeleteFeatureMutation() {
  const api = useApi();
  const { showSnackbar } = useSnackbar();

  return useApiMutation({
    mutationFn: (id: string) => api.api.deleteFeatureApiV2FeatureIdDelete({ id }),
    invalidateQueries: [{ queryKey: queryKeys.features.all() }],
    onSuccess: () => showSnackbar("Deleted successfully", "success"),
    onError: (error) => showSnackbar(error.message, "error"),
  });
}
```

---

## API Client

### Auto-Generated Client

- Generated from OpenAPI spec using `swagger-typescript-api`
- Location: `src/lib/api-client/`
- **NEVER manually edit** - regenerate with `yarn generate-api:clean`

### After Backend Changes

```bash
yarn generate-api:clean    # Regenerate API client
```

### Type Reuse

Always import types from the auto-generated client:

```typescript
// GOOD - use generated types
import { TaskResponse, RuleResponse } from "@/lib/api-client/Api";

// BAD - duplicate type definitions
interface TaskResponse { ... }
```

---

## Validation with Zod

### Schema Definition

```typescript
// schemas/featureSchemas.ts
import { z } from "zod";

export const featureFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(100).trim(),
  description: z.string().max(500).optional().or(z.literal("")),
  enabled: z.boolean().default(true),
});

export type FeatureFormValues = z.infer<typeof featureFormSchema>;
```

### Form Validation

```typescript
const handleSubmit = () => {
  const result = featureFormSchema.safeParse(formData);
  if (!result.success) {
    setErrors(result.error.flatten().fieldErrors);
    return;
  }
  mutation.mutate(result.data);
};
```

---

## Styling

### Tailwind + MUI Integration

- Use MUI components for complex UI elements
- Use Tailwind utilities for layout and spacing
- Use `cn()` utility for conditional classes

```typescript
import { cn } from "@/utils/cn";

<div className={cn(
  "p-4 rounded-lg",
  isActive && "bg-blue-100",
  isError && "border-red-500"
)} />
```

### MUI sx Prop

```typescript
<Box sx={{
  p: 3,
  display: "flex",
  gap: 2,
  "&:hover": { bgcolor: "action.hover" }
}} />
```

---

## Error Handling

### Error Boundaries

Wrap feature components with error boundaries:

```typescript
import { ErrorBoundary } from "react-error-boundary";
import { ErrorFallback } from "@/components/common/ErrorFallback";

<ErrorBoundary FallbackComponent={ErrorFallback}>
  <FeatureComponent />
</ErrorBoundary>
```

### API Errors

Handle in mutation callbacks:

```typescript
useApiMutation({
  mutationFn: ...,
  onError: (error) => {
    console.error("API Error:", error);
    showSnackbar(error.message || "An error occurred", "error");
  },
});
```

---

## TypeScript Best Practices

### Strict Mode

- No `any` type - use `unknown` and narrow
- All function parameters must have types
- All return types should be specified

### Discriminated Unions for Complex State

```typescript
// BAD
interface State {
  isLoading: boolean;
  isError: boolean;
  data?: Data;
  error?: Error;
}

// GOOD
type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: Error }
  | { status: "success"; data: Data };
```

### Type Inference

```typescript
// Use Pick, Partial, Omit for derived types
type TaskSummary = Pick<TaskResponse, "id" | "name" | "status">;
type PartialTask = Partial<TaskResponse>;
type TaskWithoutId = Omit<TaskResponse, "id">;
```

---

## Testing (Future)

Test files should follow these conventions when added:

- Location: Co-located with components or in `__tests__/`
- Naming: `ComponentName.test.tsx`
- Tools: Vitest + React Testing Library

---

## Import Order

Enforced by ESLint:

```typescript
// 1. React/external libraries
import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

// 2. Internal absolute imports (@/)
import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

// 3. Relative imports
import { FeatureTable } from "./table/FeatureTable";
import { useFeatureData } from "./hooks/useFeatureData";
import type { FeatureProps } from "./types";
```

---

## Minimize useEffect

Only use `useEffect` for:
- External system synchronization (subscriptions, event listeners)
- Data fetching (prefer TanStack Query)

**Avoid** using `useEffect` for:
- Transforming data (compute during render or useMemo)
- Handling events (use event handlers)
- Resetting state (use key prop)

---

## Common Utilities

### cn - Class Name Merging

```typescript
import { cn } from "@/utils/cn";

// Combines clsx + tailwind-merge
cn("p-4", condition && "bg-red-500", className);
```

### formatters

```typescript
import { formatDate, formatDuration } from "@/utils/formatters";

formatDate(date);           // "Jan 7, 2026"
formatDuration(seconds);    // "2h 30m"
```
