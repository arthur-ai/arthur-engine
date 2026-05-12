export class BuzzError extends Error {
  constructor(
    message: string,
    public readonly fatal = true,
  ) {
    super(message);
    this.name = 'BuzzError';
  }
}
