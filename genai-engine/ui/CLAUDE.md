# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## GenAI Engine UI

React-based frontend for the GenAI Engine, providing interfaces for task management, prompt playground, dataset management, trace visualization, and model provider configuration.

### Common Commands

```bash
# Install dependencies
yarn install

# Development server (localhost:3000)
yarn dev

# Build for production
yarn build

# Preview production build
yarn preview

# Type checking
yarn type-check

# Linting
yarn lint

# Run both type checking and linting
yarn check

# Format code
yarn format
yarn format:check

# Generate API client from backend OpenAPI spec
yarn generate-api:clean
```

### Architecture

**Tech Stack**: React 19, TypeScript 5.9, Vite, Material-UI (MUI), Tailwind CSS 4, React Router v7, TanStack Query, Yarn Berry v4

**Core Structure**:

- **Components** (`src/components/`): Feature-based organization (prompts, datasets, traces, weaviate, common)
- **Contexts** (`src/contexts/`): React Context for global state (AuthContext, TaskContext)
- **Hooks** (`src/hooks/`): Custom React hooks for API interactions and shared logic
- **API Client** (`src/client/`): Auto-generated TypeScript client from backend OpenAPI spec
- **Pages** (`src/pages/`): Top-level route components
- **Router** (`src/router.tsx`): React Router v7 configuration with protected routes

**Key Patterns**:

- **Auto-Generated API Client**: The TypeScript API client is generated from the GenAI Engine's OpenAPI spec using `yarn generate-api:clean`. Never manually edit files in `src/client/` - regenerate instead
- **Context + Hooks Architecture**: Global state (auth, tasks) lives in Context, accessed via custom hooks
- **Protected Routes**: AuthContext wraps the router and guards routes requiring authentication
- **Material-UI + Tailwind**: MUI components provide the foundation, Tailwind CSS handles custom styling
- **React Query**: TanStack Query manages server state, caching, and data synchronization
- **Monaco Editor**: Embedded code editor for prompt and rule editing
- **Type Safety**: Strict TypeScript mode enabled, all API responses are typed via generated client

**Component Organization**:

- **Common components** (`src/components/common/`): Reusable UI elements (buttons, inputs, dialogs)
- **Feature components**: Organized by domain (prompts, datasets, traces, weaviate)
- Each feature typically has: list view, detail view, create/edit forms

**Routing**:

- React Router v7 with client-side navigation
- Protected routes check authentication status before rendering
- Lazy loading for code splitting (not yet implemented but supported)

**API Integration**:

- Backend runs on configurable base URL (default: localhost:5005)
- All API calls go through the generated client
- Request/response interceptors handle authentication headers
- Error handling via React Query's error boundaries

### Development Notes

- The API client must be regenerated after backend OpenAPI spec changes
- Follow the component patterns in AGENTS.md for consistency
- Use MUI's sx prop or Tailwind classes for styling, avoid inline styles
- Authentication token is stored in localStorage and managed by AuthContext
- The app is a SPA - no server-side rendering

---

## Coding Standards

### Code Formatting

**Prettier** (`.prettierrc`):
- Trailing comma: `es5`
- Tab width: `2 spaces`
- Semicolons: enabled
- Quotes: double quotes
- Print width: `150` characters

**ESLint**:
- Import ordering: `builtin → external → internal → parent → sibling → index`
- Alphabetized imports (case-insensitive)
- Unused variables: prefix with `_` to ignore (e.g., `_unusedVar`)

Run before committing:
```bash
yarn type-check && yarn lint && yarn format
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `PromptsManagement.tsx` |
| Component files | Same as component | `PromptsManagement.tsx` |
| Folders | kebab-case | `prompts-management/` |
| Hooks | `use` prefix, camelCase | `usePrompts`, `useApiQuery` |
| Utilities | camelCase | `formatDate`, `cn` |
| Types/Interfaces | PascalCase | `PromptsTableProps` |
| Constants | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |

### Component Pattern

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

Keep related code close:

```
components/feature-name/
├── FeatureName.tsx           # Main component
├── FeatureNameHeader.tsx     # Sub-components
├── hooks/
│   ├── useFeatureData.ts     # Feature-specific hooks
│   └── useFeatureMutation.ts
├── types.ts                  # Feature-specific types
└── table/
    └── FeatureTable.tsx
```

### State Management Hierarchy

1. **Server State**: TanStack Query for API data
2. **Global State**: React Context for auth, current task
3. **Local State**: `useState` for component-level
4. **URL State**: `nuqs` for URL parameters

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

### Data Fetching with TanStack Query

Use centralized query keys:

```typescript
// lib/queryKeys.ts
export const queryKeys = {
  datasets: {
    all: () => ["datasets"] as const,
    detail: (id: string) => ["datasets", id] as const,
  },
};

// Custom hook
export function useFeatureData(id: string) {
  return useApiQuery({
    method: "getFeatureApiV2FeatureIdGet",
    args: [{ featureId: id }],
    enabled: !!id,
  });
}
```

### API Client

- Auto-generated from OpenAPI spec in `src/lib/api-client/`
- **NEVER manually edit** - regenerate with `yarn generate-api:clean`
- Always import types from generated client, don't duplicate

### Validation with Zod

```typescript
import { z } from "zod";

export const featureFormSchema = z.object({
  name: z.string().min(1, "Required").max(100).trim(),
  description: z.string().max(500).optional(),
});

export type FeatureFormValues = z.infer<typeof featureFormSchema>;
```

### Styling

Use `cn()` utility for conditional Tailwind classes:

```typescript
import { cn } from "@/utils/cn";

<div className={cn(
  "p-4 rounded-lg",
  isActive && "bg-blue-100",
  isError && "border-red-500"
)} />
```

### TypeScript Best Practices

- No `any` type - use `unknown` and narrow
- All function parameters must have types
- Use discriminated unions for complex state:

```typescript
// GOOD
type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: Error }
  | { status: "success"; data: Data };
```

### Import Order

```typescript
// 1. React/external libraries
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";

// 2. Internal absolute imports (@/)
import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

// 3. Relative imports
import { FeatureTable } from "./table/FeatureTable";
import type { FeatureProps } from "./types";
```

### Minimize useEffect

Only use for:
- External system synchronization (subscriptions, event listeners)
- Data fetching (prefer TanStack Query)

**Avoid** for:
- Transforming data (compute during render or useMemo)
- Handling events (use event handlers)
- Resetting state (use key prop)
