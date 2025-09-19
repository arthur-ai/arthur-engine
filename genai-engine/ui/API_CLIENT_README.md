# API Client Generation

This document explains how to generate and use the TypeScript API client for the Arthur GenAI Engine.

## Overview

The API client is automatically generated from the OpenAPI specification located at `../staging.openapi.json` using the `swagger-typescript-api@13.0.16` tool.

## Setup

### 1. Install Dependencies

```bash
yarn install
```

This will install the dependencies needed for generation. The `swagger-typescript-api` tool is used via npx, so no additional installation is required.

### 2. Generate the API Client

```bash
# Generate the API client
yarn generate-api

# Or clean and regenerate (removes existing client first)
yarn generate-api:clean
```

## Generated Files

After generation, you'll find the following structure in `src/lib/api-client/`:

```
src/lib/api-client/
├── api-client.ts       # Main API client with all endpoints
├── types/              # TypeScript interfaces for request/response models
└── README.md           # Generated documentation
```

## Usage

### Basic Setup

```typescript
import { Api } from '@/lib/api-client/api-client';

// Create API client instance
const api = new Api({
  baseURL: 'https://your-api-endpoint.com',
  securityWorker: (token) => token ? { headers: { Authorization: `Bearer ${token}` } } : {}
});

// Make API calls
const usage = await api.usage.getTokenUsage();
```

### Custom Configuration

```typescript
import { Api } from '@/lib/api-client/api-client';

// Create a custom API client
const api = new Api({
  baseURL: 'https://your-api-endpoint.com',
  securityWorker: (token) => token ? { headers: { Authorization: `Bearer ${token}` } } : {}
});
```

### Environment Variables

Set these environment variables in your `.env.local` file:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-api-endpoint.com
NEXT_PUBLIC_API_KEY=your-api-key
```

### Example API Calls

```typescript
import { Api } from '@/lib/api-client/api-client';

const api = new Api({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  securityWorker: (token) => token ? { headers: { Authorization: `Bearer ${token}` } } : {}
});

// Get token usage
const usage = await api.usage.getTokenUsage({
  startTime: '2024-01-01T00:00:00Z',
  endTime: '2024-01-31T23:59:59Z',
  groupBy: 'day'
});

// Handle responses
if (usage.data) {
  console.log('Token usage:', usage.data);
}
```

## Regeneration

### When to Regenerate

Regenerate the API client when:
- The OpenAPI specification (`../staging.openapi.json`) is updated
- New endpoints are added to the backend
- Request/response models change
- You want to pick up the latest generator improvements

### How to Regenerate

```bash
# Simple regeneration
yarn generate-api

# Clean regeneration (recommended for major changes)
yarn generate-api:clean
```

## Configuration

The generation command includes several TypeScript optimizations:

- **TypeScript 3+ support**: Uses modern TypeScript features
- **ES6 support**: Generates ES6-compatible code
- **Interface generation**: Creates TypeScript interfaces for all models
- **Original naming**: Preserves original property names from the OpenAPI spec
- **Separate models and API**: Organizes code into logical modules
- **String enums**: Uses string enums for better type safety

## Troubleshooting

### Common Issues

1. **Generation fails**: Make sure the OpenAPI spec file exists and is valid
2. **Import errors**: Run `yarn generate-api:clean` to ensure a fresh generation
3. **Type errors**: Check that your TypeScript version is compatible

### Manual Generation

If the yarn script fails, you can run the generator manually:

```bash
npx swagger-typescript-api@13.0.16 \
  -p ../staging.openapi.json \
  -o src/lib/api-client \
  --name api-client.ts \
  --modular \
  --axios \
  --extract-request-params \
  --extract-request-body \
  --extract-response-body \
  --extract-response-error \
  --extract-enums \
  --extract-types \
  --clean-output
```

## Integration with Next.js

The generated client is designed to work seamlessly with Next.js:

- **Server-side rendering**: Works in `getServerSideProps` and API routes
- **Client-side**: Works in React components and hooks
- **Environment variables**: Supports Next.js environment variable patterns
- **TypeScript**: Full TypeScript support with generated types

## Best Practices

1. **Don't edit generated files**: Always regenerate instead of manually editing
2. **Use the generated client**: Import from `@/lib/api-client/api-client` for the main API class
3. **Handle errors**: Always wrap API calls in try-catch blocks
4. **Type safety**: Use the generated types for request/response objects
5. **Environment config**: Use environment variables for API endpoints and keys
6. **Security**: Use the securityWorker for token-based authentication
