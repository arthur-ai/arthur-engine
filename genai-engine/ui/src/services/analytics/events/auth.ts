export interface AuthEvents {
  "Session Restored": { authentication_method: "api_key"; is_tenant: boolean };
  "Token Validation Failed": { authentication_method: "api_key"; error: string };
  "Auth Initialization Failed": { authentication_method: "api_key"; error: string };
  Login: { authentication_method: "api_key"; is_tenant: boolean };
  "Login Failed": { authentication_method: "api_key"; error: string };
  Logout: { authentication_method: "api_key" };
}
