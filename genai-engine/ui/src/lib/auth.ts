import { createAuthenticatedApiClient, Api } from "./api";
import type { MeResponse } from "./api-client/api-client";

const TOKEN_STORAGE_KEY = "arthur_auth_token";
const ME_STORAGE_KEY = "arthur_auth_me";

export type { MeResponse };

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  me: MeResponse | null;
  isTenant: boolean;
  isLoading: boolean;
  error: string | null;
}

export const TENANT_USER_ROLE = "TENANT-USER";

export function deriveIsTenant(me: MeResponse | null): boolean {
  if (!me) return false;
  return me.roles.includes(TENANT_USER_ROLE) && me.org_scope != null;
}

export class AuthService {
  private static instance: AuthService;
  private token: string | null = null;
  private me: MeResponse | null = null;
  private apiClient: Api<unknown> | null = null;

  private constructor() {
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem(TOKEN_STORAGE_KEY);
      const cachedMe = localStorage.getItem(ME_STORAGE_KEY);
      if (cachedMe) {
        try {
          this.me = JSON.parse(cachedMe) as MeResponse;
        } catch {
          localStorage.removeItem(ME_STORAGE_KEY);
        }
      }
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

  private persistMe(me: MeResponse): void {
    this.me = me;
    if (typeof window !== "undefined") {
      localStorage.setItem(ME_STORAGE_KEY, JSON.stringify(me));
    }
  }

  public async login(token: string): Promise<boolean> {
    try {
      const testClient = createAuthenticatedApiClient(token);
      const response = await testClient.users.getMeUsersMeGet();

      this.token = token;
      if (typeof window !== "undefined") {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
      }
      this.initializeApiClient();
      this.persistMe(response.data);
      return true;
    } catch (error) {
      console.error("Authentication failed:", error);
      return false;
    }
  }

  public logout(): void {
    this.token = null;
    this.me = null;
    this.apiClient = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(ME_STORAGE_KEY);
    }
  }

  public getToken(): string | null {
    return this.token;
  }

  public getMe(): MeResponse | null {
    return this.me;
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
      const response = await this.apiClient.users.getMeUsersMeGet();
      this.persistMe(response.data);
      return true;
    } catch (error) {
      console.error("Token validation failed:", error);
      this.logout();
      return false;
    }
  }
}
