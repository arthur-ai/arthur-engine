import { Experiment, type ExperimentClient, type Variant } from "@amplitude/experiment-js-client";

/**
 * Returned whenever experiments are disabled (missing deployment key) or a
 * lookup fails. All `Variant` fields are optional, so an empty object reads as
 * "no variant" and consumers fall back to their own defaults (e.g. `?? "linear"`).
 */
const EMPTY_VARIANT: Variant = {};

let experiment: ExperimentClient | null = null;
let initPromise: Promise<ExperimentClient | null> | null = null;

/**
 * Initialize the Amplitude experiment client. Returns `null` (experiments
 * disabled) when the deployment key is missing or initialization fails, so the
 * app degrades gracefully instead of throwing.
 */
const initExperiment = async (): Promise<ExperimentClient | null> => {
  const deploymentKey = import.meta.env.VITE_AMPLITUDE_DEPLOYMENT_KEY;

  if (!deploymentKey) {
    console.warn("VITE_AMPLITUDE_DEPLOYMENT_KEY not set. Amplitude experiments disabled; using default variants.");
    return null;
  }

  try {
    const client = Experiment.initializeWithAmplitudeAnalytics(deploymentKey);
    await client.fetch();
    return client;
  } catch (error) {
    console.error("Failed to initialize Amplitude experiments. Using default variants.", error);
    return null;
  }
};

export const getAmplitudeExperiment = async (): Promise<ExperimentClient | null> => {
  if (experiment) {
    return experiment;
  }

  // Memoize the in-flight init so concurrent callers share one attempt and the
  // "disabled" result is cached (no repeated warnings or network retries).
  if (!initPromise) {
    initPromise = initExperiment().then((client) => (experiment = client));
  }

  return initPromise;
};

export const getExperimentVariant = async (experimentName: string): Promise<Variant> => {
  const client = await getAmplitudeExperiment();

  if (!client) {
    return EMPTY_VARIANT;
  }

  try {
    return client.variant(experimentName);
  } catch (error) {
    console.error(`Failed to get Amplitude experiment variant "${experimentName}". Using default.`, error);
    return EMPTY_VARIANT;
  }
};
