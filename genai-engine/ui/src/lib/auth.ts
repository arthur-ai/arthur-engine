import { Configuration, TasksApi, SearchTasksRequest } from "./api-client";

const TOKEN_STORAGE_KEY = "arthur_auth_token";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

export class AuthService {
  private static instance: AuthService;
  private token: string | null = null;
  private apiClient: TasksApi | null = null;

  private constructor() {
    // Initialize token from localStorage if available
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (this.token) {
        this.initializeApiClient();
      }
    }
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  private initializeApiClient(): void {
    if (this.token) {
      const configuration = new Configuration({
        basePath: API_BASE_URL,
        accessToken: this.token,
      });
      this.apiClient = new TasksApi(configuration);
    }
  }

  public async login(token: string): Promise<boolean> {
    try {
      // Test the token by making a simple API call
      const configuration = new Configuration({
        basePath: API_BASE_URL,
        accessToken: token,
      });
      const testClient = new TasksApi(configuration);

      // Try to search for tasks with an empty request to test authentication
      const searchRequest: SearchTasksRequest = {};
      await testClient.searchTasksApiV2TasksSearchPost({
        searchTasksRequest: searchRequest,
        pageSize: 1,
        page: 1,
      });

      // If successful, save the token and initialize the client
      this.token = token;
      if (typeof window !== "undefined") {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
      }
      this.initializeApiClient();
      return true;
    } catch (error) {
      console.error("Authentication failed:", error);
      return false;
    }
  }

  public logout(): void {
    this.token = null;
    this.apiClient = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }

  public getToken(): string | null {
    return this.token;
  }

  public isAuthenticated(): boolean {
    return this.token !== null;
  }

  public getApiClient(): TasksApi | null {
    return this.apiClient;
  }

  public async validateToken(): Promise<boolean> {
    if (!this.token || !this.apiClient) {
      return false;
    }

    try {
      // Test the token by making a simple API call
      const searchRequest: SearchTasksRequest = {};
      await this.apiClient.searchTasksApiV2TasksSearchPost({
        searchTasksRequest: searchRequest,
        pageSize: 1,
        page: 1,
      });
      return true;
    } catch (error) {
      console.error("Token validation failed:", error);
      // If validation fails, clear the token
      this.logout();
      return false;
    }
  }
}
