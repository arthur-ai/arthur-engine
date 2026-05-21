import type { TriggerFactory } from "../types";

export interface TriggerRegistry {
  register: (key: string, factory: TriggerFactory) => void;
  get: (key: string) => TriggerFactory | undefined;
}

export function createTriggerRegistry(initial?: Record<string, TriggerFactory>): TriggerRegistry {
  const map = new Map<string, TriggerFactory>(Object.entries(initial ?? {}));
  return {
    register(key, factory) {
      map.set(key, factory);
    },
    get(key) {
      return map.get(key);
    },
  };
}
