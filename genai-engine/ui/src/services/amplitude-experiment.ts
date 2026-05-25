import { Experiment, type ExperimentClient } from "@amplitude/experiment-js-client";

let experiment: ExperimentClient | null = null;

export const getAmplitudeExperiment = async () => {
  if (!experiment) {
    experiment = Experiment.initializeWithAmplitudeAnalytics(import.meta.env.VITE_AMPLITUDE_DEPLOYMENT_KEY as string);

    await experiment.fetch();
  }

  return experiment;
};

export const getExperimentVariant = async (experimentName: string) => {
  const experiment = await getAmplitudeExperiment();

  return experiment.variant(experimentName);
};
