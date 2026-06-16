// Keys are camelCase on the wire today — preserved. The rest of the tour event
// stream (`task-tour.step:enter` etc.) is runtime-generated and goes through
// `trackDynamic`, not this map.
export interface TaskTourEvents {
  "task-tour.occlusion-unrecovered": { sectionId: string; stepId: string; occluderId: string };
  "task-tour.occlusion-recovered": { sectionId: string; stepId: string; occluderId: string; viaUserAction: boolean };
}
