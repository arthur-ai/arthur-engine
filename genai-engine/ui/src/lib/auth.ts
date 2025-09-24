import { createAuthenticatedApiClient, Api, SearchTasksRequest } from "./api";

const TOKEN_STORAGE_KEY = "arthur_auth_token";

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

export class AuthService {
  private static instance: AuthService;
  private token: string | null = null;
  private apiClient: Api<unknown> | null = null;

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
      this.apiClient = createAuthenticatedApiClient(this.token);
    }
  }

  public async login(token: string): Promise<boolean> {
    try {
      // Test the token by making a simple API call
      const testClient = createAuthenticatedApiClient(token);

      // Try to search for tasks with an empty request to test authentication
      const searchRequest: SearchTasksRequest = {};
      await testClient.api.searchTasksApiV2TasksSearchPost(searchRequest, {
        page_size: 1,
        page: 0,
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

  public getApiClient(): Api<unknown> | null {
    return this.apiClient;
  }

  public async validateToken(): Promise<boolean> {
    if (!this.token || !this.apiClient) {
      return false;
    }

    try {
      // Test the token by making a simple API call
      const searchRequest: SearchTasksRequest = {};
      await this.apiClient.api.searchTasksApiV2TasksSearchPost(searchRequest, {
        page_size: 1,
        page: 0,
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
