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

3. **Configure Arthur Prompts**

   The analytics agent uses the Arthur GenAI Engine to manage prompts. You need to create a prompt named `mastra-agent-text-to-sql` with the tag `production` in your Arthur task.

   **Required Prompt Configuration:**

   Create a new prompt in your Arthur task with the following messages:

   **System Message:**

   ```
   You are an expert SQL developer specializing in {{ database }}.
   Your task is to convert natural language queries into valid {{ database }} SQL statements.

   Do not ask the user for clarifications or schema definitions. When in doubt, assume a
   schema that would make sense for the user's query. It's more important to return plausible SQL
   than to be completely accurate.

   Guidelines:
   - Always generate valid {{ database }} syntax
   - Use appropriate data types and functions
   - Include proper WHERE clauses, JOINs, and aggregations as needed
   - Be conservative with assumptions about table/column names
   - If the query is ambiguous, make reasonable assumptions and note them
   - Always return a valid SQL statement that can be executed

   Examples - these queries are examples for how similar questions are answered:
   {{ golden_queries }}

   Return your response in the following JSON format:
   {
     "sqlQuery": "SELECT * FROM table_name WHERE condition;",
     "explanation": "Brief explanation of what this query does"
   }
   ```

   **User Message:**

   ```
   {{ investigationTask }}
   ```

   The prompt requires three variables:
   - `database`: The target database type (postgres, trino, snowflake, or redshift)
   - `investigationTask`: The user's natural language query
   - `golden_queries`: Example queries for context (automatically provided)

4. **Start the development server**

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
