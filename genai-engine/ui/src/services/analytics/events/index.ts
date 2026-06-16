import type { AgentExperimentEvents } from "./agent-experiments";
import type { AgentNotebookEvents } from "./agent-notebooks";
import type { AuthEvents } from "./auth";
import type { CrossLinkEvents } from "./cross-links";
import type { DatasetEvents } from "./datasets";
import type { FeedbackEvents } from "./feedback";
import type { OnboardingEvents } from "./onboarding";
import type { PlaygroundEvents } from "./playground";
import type { TaskTourEvents } from "./task-tour";
import type { TracingEvents } from "./tracing";

/**
 * The complete catalog of analytics events: wire name → property shape.
 * `undefined` means the event carries no properties (and `track` forbids a
 * properties argument). Wire names are sent to Amplitude verbatim — never
 * rename one without accepting that existing Amplitude charts break.
 */
export interface AnalyticsEvents
  extends
    AuthEvents,
    PlaygroundEvents,
    AgentExperimentEvents,
    AgentNotebookEvents,
    TracingEvents,
    DatasetEvents,
    FeedbackEvents,
    OnboardingEvents,
    TaskTourEvents,
    CrossLinkEvents {}

export type AnalyticsEventName = keyof AnalyticsEvents;
