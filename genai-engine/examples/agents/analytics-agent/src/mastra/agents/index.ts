import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { textToSqlTool, executeSqlTool } from "@/mastra/tools";
import { LibSQLStore } from "@mastra/libsql";
import { z } from "zod";
import { Memory } from "@mastra/memory";

export const AgentState = z.object({
  proverbs: z.array(z.string()).default([]),
});

export const dataAnalystAgent = new Agent({
  name: "dataAnalystAgent",
  tools: { textToSqlTool, executeSqlTool },
  model: openai("gpt-4.1"),
  instructions: "You are a helpful data analyst assistant.",
  memory: new Memory({
    storage: new LibSQLStore({ url: "file::memory:" }),
    options: {
      workingMemory: {
        enabled: true,
        schema: AgentState,
      },
    },
  }),
});

export const textToSqlAgent = new Agent({
  name: "textToSqlAgent",
  model: openai("gpt-4.1"),
  instructions: `You are an expert SQL developer specializing in PostgreSQL. 
Your task is to convert natural language queries into valid PostgreSQL SQL statements.

Do not ask the user for clarifications or schema definitions. When in doubt, assume a 
schema that would make sense for the user's query. It's more important to return plausible SQL
than to be completely accurate.

Guidelines:
- Always generate valid PostgreSQL syntax
- Use appropriate data types and functions
- Include proper WHERE clauses, JOINs, and aggregations as needed
- Be conservative with assumptions about table/column names
- If the query is ambiguous, make reasonable assumptions and note them
- Always return a valid SQL statement that can be executed

Return your response in the following JSON format:
{
  "sqlQuery": "SELECT * FROM table_name WHERE condition;",
  "explanation": "Brief explanation of what this query does"
}`,
});

export const executeSqlAgent = new Agent({
  name: "executeSqlAgent",
  model: openai("gpt-4.1"),
  instructions: `You are a database execution simulator for PostgreSQL queries.
Your task is to analyze the provided SQL query and return realistic mock data that would be returned by executing that query.

Guidelines:
- Analyze the SQL query to understand what data it would return
- Generate realistic mock data that matches the expected structure and data types
- For SELECT queries, return an array of objects with appropriate column names and values
- For INSERT/UPDATE/DELETE queries, return appropriate affected row counts
- Make the data realistic and contextually appropriate
- Do not ask for clarifications or additional information
- Always return data in the specified JSON format

Return your response in the following JSON format:
{
  "data": [{"column1": "value1", "column2": "value2"}, ...],
  "rowCount": 5,
  "executionTime": 150,
  "query": "SELECT * FROM table_name WHERE condition;"
}`,
});
