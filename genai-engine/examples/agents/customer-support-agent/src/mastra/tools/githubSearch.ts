import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { SpanType } from "@mastra/core/observability";
import { Octokit } from "@octokit/rest";

export type GitHubSearchToolResult = z.infer<typeof GitHubSearchToolResultSchema>;

const GitHubResultSchema = z.object({
  path: z.string().describe("File path in the repository"),
  repository: z.string().describe("Repository name"),
  url: z.string().describe("URL to the file on GitHub"),
  snippet: z.string().describe("Code snippet containing the match"),
  sha: z.string().optional().describe("SHA of the file"),
});

const GitHubSearchToolResultSchema = z.object({
  results: z.array(GitHubResultSchema).describe("Array of code search results from Arthur Engine repository"),
  query: z.string().describe("The search query that was executed"),
  resultsCount: z.number().describe("Number of results returned"),
});

export const githubSearchTool = createTool({
  id: "github-search",
  description: "Search the Arthur Engine GitHub repository (arthur-ai/arthur-engine) for code examples, implementation details, and source code",
  inputSchema: z.object({
    query: z.string().describe("The code search query to find relevant implementation in Arthur Engine"),
    maxResults: z.number().describe("Maximum number of results to return"),
  }),
  outputSchema: GitHubSearchToolResultSchema,
  execute: async (inputData, executionContext) => {
    const { tracingContext } = executionContext ?? {};
    try {
      // Create a search span for tracing
      const searchSpan = tracingContext?.currentSpan?.createChildSpan({
        type: SpanType.GENERIC,
        name: `github-search: ${inputData.query}`,
        input: {
          query: inputData.query,
          maxResults: inputData.maxResults,
          repository: "arthur-ai/arthur-engine",
        },
        metadata: {
          type: "code_search",
          source: "github",
        },
      });

      const startTime = Date.now();

      // Initialize Octokit client
      const octokit = new Octokit({
        auth: process.env.GITHUB_TOKEN,
      });

      // Search code in the arthur-ai/arthur-engine repository
      const searchQuery = `${inputData.query} repo:arthur-ai/arthur-engine`;
      
      const maxResults = inputData.maxResults || 5;
      
      const response = await octokit.rest.search.code({
        q: searchQuery,
        per_page: maxResults,
        sort: "indexed",
      });

      const results = await Promise.all(
        response.data.items.slice(0, maxResults).map(async (item: any) => {
          // Fetch file content to get a better snippet
          let snippet = "";
          try {
            const contentResponse = await octokit.rest.repos.getContent({
              owner: "arthur-ai",
              repo: "arthur-engine",
              path: item.path,
              ref: item.sha,
            });

            if ("content" in contentResponse.data && contentResponse.data.content) {
              // Decode base64 content
              const content = Buffer.from(
                contentResponse.data.content,
                "base64"
              ).toString("utf-8");
              
              // Extract a relevant snippet (first 500 characters or first 10 lines)
              const lines = content.split("\n").slice(0, 10);
              snippet = lines.join("\n").substring(0, 500);
            }
          } catch (error) {
            // If we can't fetch content, use the name as snippet
            snippet = `File: ${item.name}`;
          }

          return {
            path: item.path,
            repository: item.repository.full_name,
            url: item.html_url,
            snippet,
            sha: item.sha,
          };
        })
      );

      const executionTime = Date.now() - startTime;

      // End the search span with success
      searchSpan?.end({
        output: {
          resultsCount: results.length,
          results: results.map((r) => ({
            path: r.path,
            repository: r.repository,
            url: r.url,
          })),
        },
        metadata: {
          durationMs: executionTime,
          success: true,
        },
      });

      return {
        results,
        query: inputData.query,
        resultsCount: results.length,
      };
    } catch (error) {
      console.error("GitHub search tool error:", error);
      
      // Return empty results on error rather than throwing
      return {
        results: [],
        query: inputData.query,
        resultsCount: 0,
      };
    }
  },
});
