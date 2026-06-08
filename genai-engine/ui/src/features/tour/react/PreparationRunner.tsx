import { useEffect, useMemo, useState } from "react";

import type { PreparationRequest } from "../core/engine";
import type { PreparationHook, PreparationResult } from "../core/types";

import { useTour, useTourEngine } from "./useTour";

interface ActiveRequest {
  request: PreparationRequest;
  hook: PreparationHook;
}

interface MountedPrepProps {
  request: PreparationRequest;
  hook: PreparationHook;
}

/**
 * Runs a single preparation callback for the duration of a step's prep phase.
 * The callback is registered from React, but it is an ordinary async callback:
 * read app state into refs outside it rather than calling hooks inside it.
 */
function MountedPrep({ request, hook }: MountedPrepProps) {
  const { actions } = useTour();

  useEffect(() => {
    let cancelled = false;
    const onAbort = () => {
      cancelled = true;
      request.resolve({ ready: false });
    };
    request.signal.addEventListener("abort", onAbort);

    const handle = async () => {
      try {
        const result = await hook({ stepContext: request.stepContext, actions });
        if (cancelled) return;
        request.resolve(result);
      } catch (err) {
        if (cancelled) return;
        request.reject(err);
      }
    };
    void handle();

    return () => {
      request.signal.removeEventListener("abort", onAbort);
    };
    // We deliberately want this effect to fire once per `request` identity.
    // Hooks themselves can re-render via their own state — closing over a
    // stable request avoids the engine getting two callbacks for one prep.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request]);

  return null;
}

/**
 * Subscribes to the engine's `onPrepareRequested` channel and mounts the
 * matching registered hook. Lives inside `<TourHost />` so widgets and
 * preparation hooks share the same provider tree (engine context, plugin
 * stores).
 *
 * When the engine asks for a preparation key that has no registered hook we
 * resolve the request immediately as `{ ready: true }` so the step doesn't
 * deadlock — preparation is best-effort, not required.
 */
export function PreparationRunner() {
  const engine = useTourEngine();
  const [active, setActive] = useState<ActiveRequest | null>(null);

  useEffect(() => {
    return engine.onPrepareRequested((request) => {
      const hook = engine.getPreparation(request.key);
      if (!hook) {
        request.resolve({ ready: true } satisfies PreparationResult);
        return;
      }
      setActive({ request, hook });
    });
  }, [engine]);

  // Clear `active` when the request settles. We listen on the request's
  // signal so the runner unmounts the prep component as soon as the engine
  // moves on, freeing whatever React state the hook held.
  useEffect(() => {
    if (!active) return;
    const onAbort = () => setActive(null);
    active.request.signal.addEventListener("abort", onAbort);
    return () => {
      active.request.signal.removeEventListener("abort", onAbort);
    };
  }, [active]);

  // We also clear `active` after the request resolves naturally — wrap the
  // resolve / reject callbacks once we mount so cleanup happens whether the
  // hook returns ready or the engine aborts.
  const wrapped = useMemo<ActiveRequest | null>(() => {
    if (!active) return null;
    const orig = active.request;
    const proxied: PreparationRequest = {
      key: orig.key,
      stepContext: orig.stepContext,
      signal: orig.signal,
      resolve: (result) => {
        orig.resolve(result);
        setActive(null);
      },
      reject: (reason) => {
        orig.reject(reason);
        setActive(null);
      },
    };
    return { request: proxied, hook: active.hook };
  }, [active]);

  if (!wrapped) return null;
  return <MountedPrep request={wrapped.request} hook={wrapped.hook} />;
}
