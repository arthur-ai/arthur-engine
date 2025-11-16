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
