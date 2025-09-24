// Browser-compatible Weaviate client using HTTP instead of gRPC
export interface WeaviateConnection {
  url: string;
  apiKey: string;
}

export interface WeaviateCollection {
  name: string;
  description?: string;
  vectorizer?: string;
  properties: Array<{
    name: string;
    dataType: string[];
    description?: string;
  }>;
}

export interface SearchSettings {
  limit: number;
  distance: number;
  alpha?: number;
  includeVector?: boolean;
  includeMetadata?: boolean;
}

export interface SearchResult {
  id: string;
  properties: Record<string, any>;
  metadata: {
    distance?: number;
    score?: number;
    explainScore?: string;
  };
  vector?: number[];
}

export interface QueryResult {
  results: SearchResult[];
  totalResults?: number;
  queryTime?: number;
}

export class WeaviateService {
  private connection: WeaviateConnection | null = null;

  async connect(connection: WeaviateConnection): Promise<boolean> {
    try {
      this.connection = connection;

      // Test connection by getting meta information
      const response = await fetch(`${connection.url}/v1/meta`, {
        headers: {
          Authorization: `Bearer ${connection.apiKey}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return true;
    } catch (error) {
      console.error("Failed to connect to Weaviate:", error);
      this.connection = null;
      return false;
    }
  }

  async getCollections(): Promise<WeaviateCollection[]> {
    if (!this.connection) {
      throw new Error("Not connected to Weaviate");
    }

    try {
      const response = await fetch(`${this.connection.url}/v1/schema`, {
        headers: {
          Authorization: `Bearer ${this.connection.apiKey}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const schema = await response.json();

      return (
        schema.classes?.map((cls: any) => ({
          name: cls.class,
          description: cls.description,
          vectorizer: cls.vectorizer,
          properties:
            cls.properties?.map((prop: any) => ({
              name: prop.name,
              dataType: prop.dataType,
              description: prop.description,
            })) || [],
        })) || []
      );
    } catch (error) {
      console.error("Failed to get collections:", error);
      throw error;
    }
  }

  async search(
    collectionName: string,
    query: string,
    searchMethod: "nearText" | "nearVector" | "bm25" | "hybrid",
    settings: SearchSettings
  ): Promise<QueryResult> {
    if (!this.connection) {
      throw new Error("Not connected to Weaviate");
    }

    const startTime = Date.now();

    try {
      // Build GraphQL query
      let graphqlQuery = `
        query {
          Get {
            ${collectionName}(limit: ${settings.limit})
      `;

      // Add fields
      let fields = "*";
      if (settings.includeMetadata) {
        fields += " _additional { id distance score explainScore }";
      }
      if (settings.includeVector) {
        fields += " _additional { id distance score explainScore vector }";
      }

      graphqlQuery += ` ${fields}`;

      // Add search method
      switch (searchMethod) {
        case "nearText":
          graphqlQuery += ` nearText: { concepts: ["${query}"] distance: ${settings.distance} }`;
          break;
        case "bm25":
          graphqlQuery += ` bm25: { query: "${query}" }`;
          break;
        case "hybrid":
          graphqlQuery += ` hybrid: { query: "${query}" alpha: ${
            settings.alpha || 0.5
          } }`;
          break;
        default:
          throw new Error(`Unsupported search method: ${searchMethod}`);
      }

      graphqlQuery += `
            }
          }
        }
      `;

      const response = await fetch(`${this.connection.url}/v1/graphql`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.connection.apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: graphqlQuery }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      const queryTime = Date.now() - startTime;

      if (result.errors) {
        throw new Error(`GraphQL errors: ${JSON.stringify(result.errors)}`);
      }

      const results: SearchResult[] =
        result.data?.Get?.[collectionName]?.map((item: any) => ({
          id: item._additional?.id || "",
          properties: { ...item },
          metadata: {
            distance: item._additional?.distance,
            score: item._additional?.score,
            explainScore: item._additional?.explainScore,
          },
          vector: item._additional?.vector,
        })) || [];

      return {
        results,
        totalResults: results.length,
        queryTime,
      };
    } catch (error) {
      console.error("Search failed:", error);
      throw error;
    }
  }

  async getCollectionStats(collectionName: string): Promise<{
    totalObjects: number;
    vectorizer: string;
    properties: number;
  }> {
    if (!this.connection) {
      throw new Error("Not connected to Weaviate");
    }

    try {
      // Get total count using GraphQL aggregate
      const countQuery = `
        query {
          Aggregate {
            ${collectionName} {
              meta {
                count
              }
            }
          }
        }
      `;

      const countResponse = await fetch(`${this.connection.url}/v1/graphql`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.connection.apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: countQuery }),
      });

      if (!countResponse.ok) {
        throw new Error(
          `HTTP ${countResponse.status}: ${countResponse.statusText}`
        );
      }

      const countResult = await countResponse.json();
      const totalObjects =
        countResult.data?.Aggregate?.[collectionName]?.[0]?.meta?.count || 0;

      // Get collection schema
      const schemaResponse = await fetch(`${this.connection.url}/v1/schema`, {
        headers: {
          Authorization: `Bearer ${this.connection.apiKey}`,
          "Content-Type": "application/json",
        },
      });

      if (!schemaResponse.ok) {
        throw new Error(
          `HTTP ${schemaResponse.status}: ${schemaResponse.statusText}`
        );
      }

      const schema = await schemaResponse.json();
      const collection = schema.classes?.find(
        (cls: any) => cls.class === collectionName
      );

      return {
        totalObjects,
        vectorizer: collection?.vectorizer || "unknown",
        properties: collection?.properties?.length || 0,
      };
    } catch (error) {
      console.error("Failed to get collection stats:", error);
      throw error;
    }
  }

  isConnected(): boolean {
    return this.connection !== null;
  }

  getConnection(): WeaviateConnection | null {
    return this.connection;
  }

  disconnect(): void {
    this.connection = null;
  }
}

// Export a singleton instance
export const weaviateService = new WeaviateService();
