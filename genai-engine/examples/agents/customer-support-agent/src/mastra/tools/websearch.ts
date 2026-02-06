import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { AISpanType } from "@mastra/core/ai-tracing";
import axios from "axios";

export type WebsearchToolResult = z.infer<typeof WebsearchToolResultSchema>;

const SearchResultSchema = z.object({
  title: z.string().describe("Title of the search result"),
  url: z.string().describe("URL of the search result"),
  snippet: z.string().describe("Brief snippet from the search result"),
  content: z.string().describe("Full content from the search result"),
  score: z.number().optional().describe("Relevance score"),
});

const WebsearchToolResultSchema = z.object({
  results: z.array(SearchResultSchema).describe("Array of search results from Arthur AI documentation"),
  query: z.string().describe("The search query that was executed"),
  resultsCount: z.number().describe("Number of results returned"),
});

export const websearchTool = createTool({
  id: "websearch",
  description: "Search Arthur AI documentation at docs.arthur.ai for information about Arthur products, features, and usage",
  inputSchema: z.object({
    query: z.string().describe("The search query to find relevant Arthur AI documentation"),
    maxResults: z.number().describe("Maximum number of results to return"),
  }),
  outputSchema: WebsearchToolResultSchema,
  execute: async ({ context, tracingContext }) => {
    try {
      // Create a search span for tracing
      const searchSpan = tracingContext?.currentSpan?.createChildSpan({
        type: AISpanType.GENERIC,
        name: `websearch: ${context.query}`,
        input: {
          query: context.query,
          maxResults: context.maxResults,
          targetSite: "docs.arthur.ai",
        },
        metadata: {
          type: "web_search",
          source: "tavily",
        },
      });

      const startTime = Date.now();

      // Call Tavily API directly
      const response = await axios.post(
        "https://api.tavily.com/search",
        {
          api_key: process.env.TAVILY_API_KEY!,
          query: context.query,
          max_results: context.maxResults || 5,
          include_domains: ["docs.arthur.ai"],
          search_depth: "advanced",
          include_answer: false,
          include_raw_content: false,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      const results = (response.data.results || []).map((result: any) => ({
        title: result.title || "",
        url: result.url || "",
        snippet: result.content || "",
        content: result.content || "",
        score: result.score,
      }));

      const executionTime = Date.now() - startTime;

      // End the search span with success
      searchSpan?.end({
        output: {
          resultsCount: results.length,
          results: results.map((r) => ({
            title: r.title,
            url: r.url,
            snippet: r.snippet.substring(0, 200),
          })),
        },
        metadata: {
          durationMs: executionTime,
          success: true,
        },
      });

      return {
        results,
        query: context.query,
        resultsCount: results.length,
      };
    } catch (error) {
      console.error("Websearch tool error:", error);
      
      // Return empty results on error rather than throwing
      return {
        results: [],
        query: context.query,
        resultsCount: 0,
      };
    }
  },
});
