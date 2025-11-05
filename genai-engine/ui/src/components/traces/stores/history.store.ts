// history.ts
import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";

export type Level = "trace" | "span" | "session" | "user";

/** Minimal target shape your app navigates between */
export type TargetBase = { id: string | number; type: Level };

export interface HistoryEntry<TTarget extends TargetBase, TState = unknown> {
  key: string;
  target: TTarget;
  title?: string;
  state?: TState;
  ts: number; // ms
}

/** Ways to identify where to stop popping */
export type Match<TTarget extends TargetBase, TState = unknown> =
  | { key: string } // by entry key
  | Partial<TTarget> // by target fields (all specified must match)
  | ((e: HistoryEntry<TTarget, TState>, idx: number) => boolean); // custom predicate

export interface PopUntilOptions {
  /** If true, removes the matching entry too (inclusive). Default false. */
  includeMatch?: boolean;
}

export interface HistoryStore<TTarget extends TargetBase, TState = unknown> {
  entries: HistoryEntry<TTarget, TState>[];

  current(): HistoryEntry<TTarget, TState> | null;

  push: (
    target: TTarget,
    init?: Omit<HistoryEntry<TTarget, TState>, "target" | "key" | "ts">
  ) => HistoryEntry<TTarget, TState>;

  popUntil: (match: Match<TTarget, TState>, opts?: PopUntilOptions) => void;
  reset: (initial?: HistoryEntry<TTarget, TState>[]) => void;
}

function makeMatcher<TTarget extends TargetBase, TState>(
  match: Match<TTarget, TState>
): (e: HistoryEntry<TTarget, TState>, idx: number) => boolean {
  if (typeof match === "function") return match;
  if ("key" in match) {
    const key = match.key;
    return (e) => e.key === key;
  }
  // Partial<TTarget>: all provided fields must match entry.target
  const partial = match;
  return (e) => {
    for (const k in partial) {
      if (e.target[k] !== partial[k as keyof typeof partial]) return false;
    }
    return true;
  };
}

export function createHistoryStore<
  TTarget extends TargetBase = TargetBase,
  TState = unknown
>() {
  return create<HistoryStore<TTarget, TState>>()((set, get) => ({
    entries: [],

    current() {
      const arr = get().entries;
      return arr.length ? arr[arr.length - 1] : null;
    },

    push(target, init) {
      const entry: HistoryEntry<TTarget, TState> = {
        key: uuidv4(),
        target,
        title: init?.title,
        state: init?.state,
        ts: Date.now(),
      };
      set((s) => ({ entries: [...s.entries, entry] }), false);
      return entry;
    },

    popUntil(match, opts) {
      const includeMatch = opts?.includeMatch ?? false;
      const isMatch = makeMatcher(match);
      set((s) => {
        if (s.entries.length === 0) return s;

        let targetIdx = -1;
        for (let i = s.entries.length - 1; i >= 0; i--) {
          if (isMatch(s.entries[i]!, i)) {
            targetIdx = i;
            break;
          }
        }

        if (targetIdx === -1) return { entries: [] };

        const keepUntil = includeMatch ? targetIdx : targetIdx + 1;
        return { entries: s.entries.slice(0, keepUntil) };
      }, false);
    },

    reset(initial) {
      set(() => ({ entries: initial?.slice() ?? [] }), false);
    },
  }));
}

export const useTracesHistoryStore = createHistoryStore<TargetBase>();
