// Keys are camelCase on the wire today — preserved. The rest of the tour event
// stream (`task-tour.step:enter` etc.) is runtime-generated and goes through
// `trackDynamic`, not this map.
export interface TaskTourEvents {
  "task-tour.occlusion-unrecovered": { sectionId: string; stepId: string; occluderId: string };
  "task-tour.occlusion-recovered": { sectionId: string; stepId: string; occluderId: string; viaUserAction: boolean };
  // Errored/stuck signals (playbook path P5). `render_error` is a React render
  // crash in the tour surfaces caught by the ErrorBoundary in `TaskTour`;
  // `tour/error` covers non-render failures (e.g. engine construction).
  "task-tour.render_error": { message: string; componentStack?: string; sectionId?: string; stepId?: string };
  "tour/error": { phase: "init" | "prep" | "runtime"; message: string; sectionId?: string; stepId?: string };
}
