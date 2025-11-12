/**
 * Global telemetry context using AsyncLocalStorage
 * This allows per-request userId/sessionId to be accessible anywhere in the request lifecycle
 */
import { AsyncLocalStorage } from 'async_hooks';

export interface TelemetryContext {
  userId?: string;
  sessionId?: string;
}

const asyncLocalStorage = new AsyncLocalStorage<TelemetryContext>();

export function runWithTelemetryContext<T>(
  context: TelemetryContext,
  fn: () => T
): T {
  return asyncLocalStorage.run(context, fn);
}

export function getTelemetryContext(): TelemetryContext | undefined {
  return asyncLocalStorage.getStore();
}

