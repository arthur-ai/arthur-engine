const PERSISTED_STORE_KEYS = [
  "arthur-user-settings",
  "arthur-theme",
  "arthur-task-list",
  "arthur-tour-panel",
] as const;

const STANDALONE_KEYS = [
  "arthur:task-tour:status",
  "task-tour:recipient-name",
] as const;

const DYNAMIC_KEY_PREFIXES = ["traces-welcome-"] as const;

export function isDemoUser(demoMode: boolean, isTenant: boolean): boolean {
  return demoMode && isTenant;
}

export function clearDemoSessionState(): void {
  if (typeof window === "undefined") return;

  for (const key of PERSISTED_STORE_KEYS) {
    localStorage.removeItem(key);
  }
  for (const key of STANDALONE_KEYS) {
    localStorage.removeItem(key);
  }

  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && DYNAMIC_KEY_PREFIXES.some((prefix) => key.startsWith(prefix))) {
      keysToRemove.push(key);
    }
  }
  for (const key of keysToRemove) {
    localStorage.removeItem(key);
  }
}
