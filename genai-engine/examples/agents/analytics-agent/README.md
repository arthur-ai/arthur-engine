# Analytics Agent - CopilotKit <> Mastra Starter

This is a starter template for building AI agents using [Mastra](https://mastra.ai) and [CopilotKit](https://copilotkit.ai). It provides a modern Next.js application with integrated AI capabilities and a beautiful UI for analytics and data visualization.

## Prerequisites

- Node.js 18+
- Yarn package manager

## Getting Started

1. **Set up environment variables**

   Create a `.env` file in this directory and add the following environment variables:

   ```bash
   # Copy the example file
   cp .env.example .env
   ```

   Then edit the `.env` file with your actual values:

   ```bash
   # OpenAI API Configuration
   OPENAI_API_KEY=your-openai-api-key-here

   # Arthur Engine Configuration
   ARTHUR_BASE_URL=https://your-arthur-instance.com
   ARTHUR_API_KEY=your-arthur-api-key-here
   ARTHUR_TASK_ID=your-arthur-task-id-here

   # Logging Configuration (optional)
   LOG_LEVEL=info
   ```

2. **Install dependencies**

   ```bash
   yarn install
   ```

3. **Start the development server**

   ```bash
   yarn dev
   ```

   This will start both the UI and agent servers concurrently.

## Available Scripts

The following scripts can be run using yarn:

- `yarn dev` - Starts both UI and agent servers in development mode
- `yarn dev:debug` - Starts development servers with debug logging enabled
- `yarn build` - Builds the application for production
- `yarn start` - Starts the production server
- `yarn lint` - Runs ESLint for code linting

## Documentation

- [Mastra Documentation](https://mastra.ai/en/docs) - Learn more about Mastra and its features
- [CopilotKit Documentation](https://docs.copilotkit.ai) - Explore CopilotKit's capabilities
- [Next.js Documentation](https://nextjs.org/docs) - Learn about Next.js features and API

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
