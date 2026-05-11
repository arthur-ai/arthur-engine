import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import {
  textToSqlTool,
  executeSqlTool,
  generateGraphTool,
} from "@/mastra/tools";
import { z } from "zod";

export const AgentState = z.object({
  proverbs: z.array(z.string()).default([]),
});

/**
 * Generates a natural language summary of SQL query results.
 * When a previous guardrail check was blocked, the blockedReason is passed in
 * as additional context so the LLM can self-correct on retry.
 */
export const generateSqlSummaryAgent = new Agent({
  name: "generateSqlSummaryAgent",
  model: openai("gpt-4.1"),
  instructions: `You summarize SQL query results in clear, concise natural language.
You will receive the SQL query and its result data. Report only what the data actually shows — use the exact numbers provided, do not round, estimate, or invent values.
If you are given a correction note explaining a previous mistake, address it directly and produce an accurate summary this time.`,
});

export const dataAnalystAgent = new Agent({
  name: "dataAnalystAgent",
  tools: { textToSqlTool, executeSqlTool, generateGraphTool },
  model: openai("gpt-4.1"),
  instructions:
    "You are a helpful data analyst assistant. Please use the textToSqlTool to convert natural language queries into PostgreSQL SQL statements and the executeSqlTool to execute the SQL query and return the results. Once you have the results, please generate a graph to visualize the results using the createGraphTool. Also always respond in english no matter the language the user speaks. If executeSqlTool returns a guardrailResult with blocked=true, inform the user that Arthur Engine's guardrails detected a hallucination and display the blockedReason.",
});

export const textToSqlAgent = new Agent({
  name: "textToSqlAgent",
  model: openai("gpt-5-mini"),
  instructions: "",
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

export const generateGraphAgent = new Agent({
  name: "generateGraphAgent",
  model: openai("gpt-4.1"),
  instructions: `You are a data visualization expert specializing in creating appropriate graphs from SQL query results.
Your task is to analyze the provided SQL query and its results to determine the best graph type and configuration.

Guidelines:
- Analyze the data structure and content to determine the most appropriate graph type
- Consider the data types: use bar charts for categorical data, line charts for time series, pie charts for proportions, scatter plots for correlations
- Choose appropriate x and y axes based on the data columns
- Generate a meaningful title that describes what the graph shows
- Process the data to ensure it's in the correct format for visualization
- Make the graph type selection based on the nature of the data, not just the query type
- Do not ask for clarifications or additional information

Graph Type Guidelines:
- "bar": Use for categorical comparisons, counts, or discrete data
- "line": Use for time series, trends, or continuous data over time
- "pie": Use for showing proportions or percentages of a whole
- "scatter": Use for showing correlations between two numeric variables
- "area": Use for showing cumulative data or stacked values over time

Return your response in the following JSON format:
{
  "graphType": "bar",
  "title": "Sales by Category",
  "xAxis": "category",
  "yAxis": "total_sales",
  "data": [{"category": "Electronics", "total_sales": 15000}, ...],
  "description": "This bar chart shows the total sales for each product category"
}`,
});
