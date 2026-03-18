export class ArthurAPIError extends Error {
  public readonly statusCode: number;
  constructor(statusCode: number, detail: string) {
    super(`HTTP ${statusCode}: ${detail}`);
    this.name = "ArthurAPIError";
    this.statusCode = statusCode;
  }
}
