# Arthur Engine UI - Cursor Rules

This is a React 19 + TypeScript + Vite application for the Arthur Engine GenAI platform. Follow these best practices and conventions when working on this project.

## 🏗️ Project Architecture

### Tech Stack

- **React 19** with TypeScript
- **Vite** for build tooling and dev server
- **Tailwind CSS 4** for styling
- **Material-UI (MUI)** for component library
- **React Router v7** for routing
- **Axios** for HTTP requests
- **Framer Motion** for animations
- **Monaco Editor** for code editing
- **Yarn 4** for package management

### Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── prompts/        # Prompt-specific components
│   └── weaviate/       # Weaviate-specific components
├── contexts/           # React Context providers
├── hooks/              # Custom React hooks
├── lib/                # Utilities and API client
│   └── api-client/     # Auto-generated API client
└── assets/             # Static assets
```

## 🎯 Code Style & Conventions

### TypeScript

- Use **strict TypeScript** with full type safety
- Prefer `interface` over `type` for object shapes
- Use proper generic constraints and utility types
- Always type function parameters and return values
- Use `React.FC<Props>` for functional components
- Use `ReactNode` for children props

### React Patterns

- Use **functional components** with hooks
- Prefer **custom hooks** for reusable logic
- Use **React Context** for global state management
- Implement **error boundaries** for error handling
- Use **React.memo** for performance optimization when needed
- Follow **React 19** patterns and best practices

### Component Organization

- **One component per file** with matching filename
- Use **PascalCase** for component names and files
- Group related components in subdirectories
- Export components as **named exports**
- Use **barrel exports** (index.ts) for clean imports

### File Naming

- Components: `ComponentName.tsx`
- Hooks: `useHookName.ts`
- Contexts: `ContextName.tsx`
- Utilities: `utilityName.ts`
- Types: `types.ts` or co-located with components

## 🎨 Styling Guidelines

### Material-UI (MUI) Components

- **Use MUI components whenever possible** for consistent design and functionality
- Prefer **MUI components** over custom implementations for common UI patterns
- Use **MUI theming** for consistent color schemes and typography
- Leverage **MUI's built-in accessibility** features and ARIA support
- Use **MUI icons** from `@mui/icons-material` for consistent iconography

### Tailwind CSS

- Use **Tailwind CSS 4** utility classes for custom styling and spacing
- Prefer **utility-first** approach over custom CSS
- Use **responsive design** with mobile-first approach
- Follow **design system** patterns from existing components
- Use **semantic color names** (gray-50, blue-600, etc.)

### Component Styling

- Use **MUI components** as the foundation, then customize with Tailwind utilities
- Use **className** prop for additional Tailwind styling on MUI components
- Prefer **Tailwind utilities** over custom CSS for spacing and layout
- Use **CSS modules** only when necessary for complex custom styling
- Follow **consistent spacing** patterns (p-4, m-2, etc.)
- Use **semantic HTML** elements with proper accessibility

## 🔧 API & Data Management

### API Client

- Use **auto-generated API client** from OpenAPI spec
- Create **authenticated API clients** via `useApi()` hook
- Handle **loading states** and **error states** consistently
- Use **TypeScript types** from API client
- Implement **proper error handling** with user feedback

### State Management

- Use **React Context** for global state (auth, tasks)
- Use **local state** for component-specific data
- Implement **loading and error states** consistently
- Use **custom hooks** for complex state logic
- Follow **single source of truth** principle

### Data Fetching

- Use **async/await** for API calls
- Implement **proper error handling**
- Use **loading states** during API calls
- Cache **API responses** when appropriate
- Use **React Query** patterns for complex data fetching

## 🛣️ Routing & Navigation

### React Router v7

- Use **BrowserRouter** for client-side routing
- Implement **protected routes** with authentication
- Use **nested routes** for complex layouts
- Handle **route parameters** with TypeScript
- Use **Navigate** component for redirects

### Navigation Patterns

- Use **consistent navigation** patterns
- Implement **breadcrumbs** for deep navigation
- Handle **back navigation** properly
- Use **active states** for current page indication
- Implement **proper URL structure**

## 🔐 Authentication & Security

### Auth Context

- Use **AuthContext** for authentication state
- Implement **token-based authentication**
- Handle **token validation** and refresh
- Use **protected routes** for authenticated pages
- Implement **proper logout** functionality

### Security Best Practices

- **Never store sensitive data** in localStorage
- Use **secure token storage**
- Implement **proper CORS** handling
- Validate **user permissions** on API calls
- Use **HTTPS** in production

## 🧪 Testing & Quality

### Code Quality

- Use **ESLint** with TypeScript rules
- Follow **import ordering** conventions
- Use **consistent code formatting**
- Implement **proper error handling**
- Use **TypeScript strict mode**

### Performance

- Use **React.memo** for expensive components
- Implement **proper key props** for lists
- Use **lazy loading** for large components
- Optimize **bundle size** with code splitting
- Use **proper dependency arrays** in hooks

## 📦 Dependencies & Build

### Package Management

- Use **Yarn 4** for package management
- Keep **dependencies up to date**
- Use **exact versions** for critical dependencies
- Implement **proper peer dependencies**
- Use **workspace patterns** for monorepos

### Build & Development

- Use **Vite** for fast development
- Implement **hot module replacement**
- Use **TypeScript** for type checking
- Follow **ESLint** rules for code quality
- Use **proper environment variables**

## 🚀 Development Workflow

### Git & Version Control

- Use **conventional commits** for commit messages
- Implement **proper branching** strategy
- Use **pull requests** for code review
- Follow **semantic versioning** for releases
- Use **proper .gitignore** patterns

### Code Review

- Review **TypeScript types** and interfaces
- Check **component props** and state management
- Verify **error handling** and loading states
- Ensure **accessibility** compliance
- Test **responsive design** on different screen sizes

## 📝 Documentation

### Code Documentation

- Use **JSDoc comments** for complex functions
- Document **component props** with TypeScript
- Use **README files** for component libraries
- Document **API integration** patterns
- Use **inline comments** for complex logic

### Component Documentation

- Document **component usage** examples
- Explain **prop types** and requirements
- Document **state management** patterns
- Use **TypeScript interfaces** for documentation
- Provide **usage examples** in comments

## 🔄 API Integration

### OpenAPI Client

- Use **auto-generated client** from OpenAPI spec
- Regenerate client when **API changes**
- Use **TypeScript types** from generated client
- Implement **proper error handling**
- Use **consistent API patterns**

### API Patterns

- Use **async/await** for API calls
- Implement **proper loading states**
- Handle **API errors** gracefully
- Use **TypeScript types** for API responses
- Implement **retry logic** for failed requests

## 🎯 Best Practices Summary

1. **Always use TypeScript** with strict type checking
2. **Follow React 19 patterns** and best practices
3. **Use MUI components whenever possible** for consistent UI patterns
4. **Use Tailwind CSS** for custom styling and spacing
5. **Implement proper error handling** and loading states
6. **Use custom hooks** for reusable logic
7. **Follow consistent naming** conventions
8. **Implement proper accessibility** features
9. **Use semantic HTML** elements
10. **Follow security best practices**
11. **Write clean, maintainable code**

## 🚫 Anti-Patterns to Avoid

- Don't use **any** type in TypeScript
- Don't **mutate props** or state directly
- Don't use **inline styles** when Tailwind utilities exist
- Don't **ignore ESLint warnings**
- Don't use **class components** (use functional components)
- Don't **hardcode API URLs** or configuration
- Don't **skip error handling** in API calls
- Don't use **var** declarations (use let/const)
- Don't **ignore accessibility** requirements
- Don't **commit console.log** statements
- Don't **create custom components** when MUI equivalents exist
- Don't **ignore MUI theming** in favor of custom CSS

Remember: This is a production application serving real users. Always prioritize code quality, performance, and user experience.
