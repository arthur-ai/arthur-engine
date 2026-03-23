import { textToSqlTool, TextToSqlToolResult } from "./textToSql";
import { executeSqlTool, ExecuteSqlToolResult } from "./executeSql";
import { generateGraphTool, GenerateGraphToolResult } from "./generateGraph";
import { weatherTool, WeatherToolResult } from "./weather";

export { textToSqlTool, executeSqlTool, generateGraphTool, weatherTool };
export type {
  TextToSqlToolResult,
  ExecuteSqlToolResult,
  GenerateGraphToolResult,
  WeatherToolResult,
};
