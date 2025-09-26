# API Client Library

This library provides a centralized way to create and configure API clients for the Arthur GenAI Engine. It's designed to be used by all components and services throughout the application.

## Overview

The API client library consists of:
- **Centralized API client creation** (`/src/lib/api.ts`)
- **React hooks for easy integration** (`/src/hooks/useApi.ts`)
- **Type-safe API calls** with full TypeScript support

## Quick Start

### Using the API Client Directly

```typescript
import { createAuthenticatedApiClient } from '@/lib/api';

// Create an authenticated client
const api = createAuthenticatedApiClient('your-token-here');

// Make API calls
const tasks = await api.api.searchTasksApiV2TasksSearchPost({}, { page_size: 10 });
```

### Using React Hooks (Recommended)

```typescript
import { useApi } from '@/hooks/useApi';

function MyComponent() {
  const api = useApi(); // Automatically uses current user's token

  useEffect(() => {
    if (api) {
      // Make authenticated API calls
      api.api.searchTasksApiV2TasksSearchPost({}, { page_size: 10 });
    }
  }, [api]);

  return <div>...</div>;
}
```

## API Reference

### Core Functions

#### `createApiClient(config)`
Creates a configured API client with custom options.

```typescript
const api = createApiClient({
  baseURL: 'https://custom-api.com',
  token: 'custom-token'
});
```

#### `createAuthenticatedApiClient(token, baseURL?)`
Creates an API client with a specific authentication token.

```typescript
const api = createAuthenticatedApiClient('your-token');
```


### React Hooks

#### `useApi()`
Returns an authenticated API client using the current user's token from the auth context.

```typescript
const api = useApi(); // Returns Api<any> | null
```


#### `useApiWithToken(token)`
Returns an API client with a specific token.

```typescript
const api = useApiWithToken('specific-token'); // Returns Api<any>
```

## Configuration

### Environment Variables

Set the API base URL in your `.env.local` file:

```env
# For local development
NEXT_PUBLIC_API_BASE_URL=http://localhost:8435

# For production, this can be omitted to use the current browser domain
# NEXT_PUBLIC_API_BASE_URL=https://your-api-endpoint.com
```

### Default Configuration

- **Base URL**: Current browser domain (or from `NEXT_PUBLIC_API_BASE_URL` for local development)
- **Authentication**: Bearer token in `Authorization` header (required for all endpoints)
- **Content Type**: `application/json`

### Domain-Based API Routing

The API client automatically uses the current browser domain as the base URL. This means:

- **Production**: If your app is hosted at `https://app.arthur.ai`, API calls will go to `https://app.arthur.ai`
- **Local Development**: Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8435` to override the default behavior
- **Custom Domains**: Set `NEXT_PUBLIC_API_BASE_URL` to point to your specific API endpoint

## Usage Examples

### Fetching Tasks

```typescript
import { useApi } from '@/hooks/useApi';

function TasksList() {
  const api = useApi();
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    const fetchTasks = async () => {
      if (api) {
        const response = await api.api.searchTasksApiV2TasksSearchPost({}, {
          page_size: 50,
          page: 1,
        });
        setTasks(response.data.tasks);
      }
    };

    fetchTasks();
  }, [api]);

  return (
    <div>
      {tasks.map(task => (
        <div key={task.id}>{task.name}</div>
      ))}
    </div>
  );
}
```

### Creating a New Task

```typescript
import { useApi } from '@/hooks/useApi';

function CreateTaskForm() {
  const api = useApi();

  const handleSubmit = async (taskData) => {
    if (api) {
      await api.api.createTaskApiV2TasksPost(taskData);
      // Handle success
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
    </form>
  );
}
```

### Error Handling

```typescript
import { useApi } from '@/hooks/useApi';

function MyComponent() {
  const api = useApi();

  const fetchData = async () => {
    try {
      if (api) {
        const response = await api.api.searchTasksApiV2TasksSearchPost({});
        // Handle success
      }
    } catch (error) {
      if (error.response?.status === 401) {
        // Handle authentication error
        console.error('Authentication failed');
      } else {
        // Handle other errors
        console.error('API error:', error);
      }
    }
  };

  return <div>...</div>;
}
```

## Type Safety

The library exports all necessary types from the generated API client:

```typescript
import { 
  TaskResponse, 
  SearchTasksRequest, 
  NewTaskRequest,
  RuleResponse 
} from '@/lib/api';

// Use types for better TypeScript support
const task: TaskResponse = {
  id: 'task-1',
  name: 'My Task',
  // ... other properties
};
```

## Best Practices

1. **Use React Hooks**: Prefer `useApi()` over direct client creation in components
2. **Handle Loading States**: Always check if the API client is available before making calls
3. **Error Handling**: Wrap API calls in try-catch blocks
4. **Type Safety**: Use the exported types for better development experience
5. **Authentication**: All endpoints require authentication - let the auth context manage tokens automatically

## Migration Guide

### From Direct API Client Usage

**Before:**
```typescript
import { Api } from '@/lib/api-client/api-client';

const api = new Api({
  baseURL: 'http://localhost:8000',
  securityWorker: (token) => token ? { headers: { Authorization: `Bearer ${token}` } } : {}
});
```

**After:**
```typescript
import { useApi } from '@/hooks/useApi';

const api = useApi(); // Automatically configured
```

### From AuthService API Client

**Before:**
```typescript
const authService = AuthService.getInstance();
const apiClient = authService.getApiClient();
```

**After:**
```typescript
const api = useApi(); // Cleaner and more React-friendly
```

## Troubleshooting

### Common Issues

1. **API client is null**: Make sure you're authenticated and the auth context is properly set up
2. **Type errors**: Ensure you're importing types from `@/lib/api` not the generated client directly
3. **Authentication failures**: Check that your token is valid and the API endpoint is correct

### Debug Mode

Enable debug logging by setting the environment variable:

```env
NEXT_PUBLIC_DEBUG_API=true
```

This will log all API requests and responses to the console.
