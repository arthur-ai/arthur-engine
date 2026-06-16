import { useMemo, useState } from "react";

import type { RuleResponse } from "@/lib/api-client/api-client";

/**
 * Tracks staged enable/disable changes to a task's guardrail rules.
 *
 * The server rules are the source of truth; local toggles are layered on top as a
 * draft. Only genuine diffs — a desired `enabled` that differs from the server value —
 * count as unsaved changes, so toggling a rule back to its server state clears it, and
 * stale entries (rules deleted on the server, or values that match again after a
 * refetch) self-prune. Everything is derived during render; no effects.
 */
export function useGuardrailDraft(rules: RuleResponse[]) {
  // ruleId -> desired enabled. May contain inert entries that match the server value;
  // `changes` below filters those out so they don't register as unsaved changes.
  const [pending, setPending] = useState<Record<string, boolean>>({});

  const changes = useMemo<Record<string, boolean>>(() => {
    const out: Record<string, boolean> = {};
    for (const rule of rules) {
      const serverEnabled = rule.enabled ?? true;
      if (rule.id in pending && pending[rule.id] !== serverEnabled) {
        out[rule.id] = pending[rule.id];
      }
    }
    return out;
  }, [rules, pending]);

  const draftRules = useMemo<RuleResponse[]>(
    () => rules.map((rule) => ({ ...rule, enabled: pending[rule.id] ?? rule.enabled ?? true })),
    [rules, pending]
  );

  const setEnabled = (rule: RuleResponse, enabled: boolean) => {
    setPending((prev) => ({ ...prev, [rule.id]: enabled }));
  };

  const discard = () => setPending({});

  return {
    draftRules,
    setEnabled,
    discard,
    changes,
    hasUnsavedChanges: Object.keys(changes).length > 0,
  };
}
