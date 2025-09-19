# Authentication Setup

This Next.js application includes a complete authentication system that protects the application and validates API tokens against the Arthur GenAI Engine backend.

## Features

- **Token-based Authentication**: Users enter their API token through a login form
- **Automatic Token Validation**: The app validates tokens by making API calls to the backend
- **Persistent Storage**: Valid tokens are stored in localStorage for convenience
- **Automatic Logout**: Invalid or expired tokens automatically log the user out
- **Protected Routes**: The entire application is protected behind authentication

## How It Works

1. **Initial Load**: The app checks localStorage for an existing token
2. **Token Validation**: If a token exists, it's validated by making a test API call to list tasks
3. **Login Required**: If no token exists or validation fails, the login page is shown
4. **Dashboard Access**: Once authenticated, users can access the main dashboard

## API Integration

The authentication system uses the generated API client to:
- Test token validity by calling the `searchTasksApiV2TasksSearchPost` endpoint
- Fetch and display tasks in the dashboard
- Handle authentication errors gracefully

## Configuration

### Environment Variables

Create a `.env.local` file in the UI directory with:

```env
# API Base URL - Update this to point to your Arthur GenAI Engine backend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### API Client

The authentication system automatically configures the API client with:
- The correct base URL from environment variables
- Bearer token authentication using the user's token
- Proper error handling for authentication failures

## Components

- **AuthProvider**: React context that manages authentication state
- **AuthGuard**: Component that protects routes and shows login when needed
- **LoginPage**: Login form for entering API tokens
- **Dashboard**: Main application interface (shown after authentication)

## Security Features

- Tokens are stored securely in localStorage
- Automatic token validation on app startup
- Graceful handling of expired or invalid tokens
- No sensitive data exposed in the UI
- Proper error messages for authentication failures

## Usage

1. Start the application: `yarn dev`
2. Navigate to the app in your browser
3. Enter your API token when prompted
4. The app will validate the token and show the dashboard if successful
5. Use the logout button to clear your session

## Error Handling

The system handles various error scenarios:
- Invalid tokens
- Network connectivity issues
- Backend API errors
- Expired tokens

All errors are displayed to the user with appropriate messaging.

