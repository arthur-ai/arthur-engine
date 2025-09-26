# GenAI Engine UI

A React + TypeScript + Vite frontend application for the Arthur GenAI Engine.

## Prerequisites

- Node.js (version 18 or higher)
- npm or yarn package manager

## Local Development Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Start the Development Server

```bash
npm run dev
```

The development server will start on `http://localhost:3000` and will automatically reload when you make changes to the source code.

### 3. Available Scripts

- `npm run dev` - Start the development server with hot module replacement
- `npm run build` - Build the application for production
- `npm run preview` - Preview the production build locally
- `npm run lint` - Run ESLint to check for code quality issues
- `npm run generate-api` - Generate TypeScript API client from OpenAPI spec
- `npm run generate-api:clean` - Clean and regenerate the API client

### 4. API Client Generation

The UI uses an auto-generated TypeScript client based on the OpenAPI specification. To regenerate the API client:

```bash
npm run generate-api:clean
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
- **Tailwind CSS** - Styling
- **React Router** - Client-side routing
- **Framer Motion** - Animations
- **Axios** - HTTP client
- **ESLint** - Code linting

## Development Notes

- The development server runs on port 3000 and accepts external connections
- Hot module replacement is enabled for fast development
- TypeScript strict mode is enabled
- ESLint is configured with React-specific rules
- The build output is optimized for single-page application routing

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory, ready for deployment.
