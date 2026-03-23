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

### TanStack Form

The codebase uses TanStack Form via custom wrappers in `src/components/traces/components/filtering/hooks/form.tsx`.

**Core hooks:**

- `useAppForm(options)` — creates a form with typed field components. Options: `defaultValues`, `validators`, `onSubmit`
- `withForm({ ...formOpts, props?, render })` — HOC for child components receiving the form. `props` declares extra props (with defaults) passed to render alongside `form`. Use named functions for render to satisfy ESLint hook rules. Prefer `withForm` over `withFieldGroup` for sub-components that need to display validation errors (proper error types via form-level validators).
- `withFieldGroup({ defaultValues, props?, render })` — HOC for reusable field groups. Render receives `group` with scoped `AppField`. **Caveat:** error types resolve to `never` — no `.message` property. Use `withForm` with absolute field paths instead when error display is needed.

**Field rendering:**

- `form.AppField name="path"` — typed field; children receive `field` with `state.value`, `handleChange`, `handleBlur`, `state.meta.errors`
- `form.Subscribe selector={fn}` — reactive subscription for conditional rendering
- `useStore(form.store, selector)` — direct store read (import from `@tanstack/react-form`)

**Validation:**

- Zod v4 schemas — use `{ error: "..." }` for custom messages (not `{ message: "..." }`). Use `path: ["field"]` on `.refine()` to target a specific nested field.
- `formApi.parseValuesWithSchema(schema)` (form-level) or `fieldApi.parseValueWithSchema(schema)` (field-level)
- Form-level validators can return `{ fields: { "path": error }, form: { key: error } }` — field errors auto-propagate to `field.state.meta.errors`
- Display: `error={field.state.meta.errors.length > 0}` + `helperText={field.state.meta.errors[0]?.message}` on MUI TextField
- **Clearing stale form-level errors:** `resetField()` does NOT clear errors from form-level validators (`parseValuesWithSchema`). Use `setFieldMeta` to explicitly clear `errorMap.onSubmit`:
  ```tsx
  form.setFieldMeta(path, (prev) => ({ ...prev, errorMap: { ...prev.errorMap, onSubmit: undefined } }));
  ```

**Form state:**

- `form.state.isDirty` — persistent dirty (true once any field changed, even if reverted)
- `form.state.isSubmitting`, `form.state.canSubmit`, `form.state.isValid`

**Multi-step pattern:**

- A `section` field tracks the current step. Forward navigation uses `form.handleSubmit()` (triggers validation). Back navigation sets section directly via `form.setFieldValue("section", prev)` (skips validation).

### Before Committing (REQUIRED - CI Enforced)

Always run and ensure these pass before committing UI changes:

```bash
yarn check  # Runs type-check, lint, and format:check
```

Fix any errors before committing. CI will block PRs with failures.

If you need to auto-fix formatting issues, run `yarn format` first.

### Development Notes

- The API client must be regenerated after backend OpenAPI spec changes
- Follow the component patterns in AGENTS.md for consistency
- Use MUI's sx prop or Tailwind classes for styling, avoid inline styles
- Authentication token is stored in localStorage and managed by AuthContext
- The app is a SPA - no server-side rendering
