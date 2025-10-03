# GenAI Engine UI

A React + TypeScript + Vite frontend application for the Arthur GenAI Engine.

## Prerequisites

- Node.js (version 18 or higher)
- Yarn (v4.9.2+ recommended)

## Local Development Setup

### 1. Install Dependencies

```bash
yarn install
```

Or simply:

```bash
yarn
```

### 2. Start the Development Server

```bash
yarn dev
```

The development server will start on `http://localhost:3000` and will automatically reload when you make changes to the source code.

### 3. Available Scripts

- `yarn dev` - Start the development server with hot module replacement
- `yarn build` - Build the application for production
- `yarn preview` - Preview the production build locally
- `yarn lint` - Run ESLint to check for code quality issues
- `yarn type-check` - Run TypeScript type checking
- `yarn check` - Run both type checking and linting
- `yarn generate-api` - Generate TypeScript API client from OpenAPI spec
- `yarn generate-api:clean` - Clean and regenerate the API client

### 4. API Client Generation

The UI uses an auto-generated TypeScript client based on the OpenAPI specification. To regenerate the API client:

```bash
yarn generate-api:clean
```

This will:

- Remove the existing API client
- Generate a new client from `../staging.openapi.json`
- Create TypeScript types and Axios-based HTTP client

## Project Structure

```
src/
├── lib/
│   └── api-client/     # Auto-generated API client
├── components/         # React components
├── pages/             # Page components
├── hooks/             # Custom React hooks
├── utils/             # Utility functions
└── types/             # TypeScript type definitions
```

## Technology Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS v4** - Modern utility-first CSS
- **React Router v7** - Client-side routing
- **Framer Motion** - Animations
- **Axios** - HTTP client
- **ESLint** - Code linting
- **Yarn Berry (v4)** - Package manager

## Development Notes

- The development server runs on port 3000 and accepts external connections
- Hot module replacement is enabled for fast development
- TypeScript strict mode is enabled
- ESLint is configured with React-specific rules
- The build output is optimized for single-page application routing
- Using Yarn Berry (v4) with PnP for faster installs and better disk efficiency

## Building for Production

```bash
yarn build
```

The built files will be in the `dist/` directory, ready for deployment.

## Package Manager

This project uses **Yarn Berry (v4.9.2+)**. The version is enforced via the `packageManager` field in `package.json`.

If you don't have Yarn installed:

```bash
corepack enable
corepack prepare yarn@4.9.2 --activate
```
