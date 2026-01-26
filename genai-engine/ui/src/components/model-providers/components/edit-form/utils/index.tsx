import { CredentialsSchema } from "../form";

export const parseCredentials = async (file: File) => {
  try {
    const fileContents = await file.text();
    const parsedJson = JSON.parse(fileContents);
    return CredentialsSchema.safeParseAsync(parsedJson);
  } catch {
    return { success: false, error: "Invalid credentials file" } as const;
  }
};
