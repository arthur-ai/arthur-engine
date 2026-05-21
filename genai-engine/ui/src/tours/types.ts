export type AnyTourEvents = Record<string, unknown>;

type TourStepBase<Events extends AnyTourEvents> = {
  id: string;
  route: string;
  routeParams?: Record<string, string>;
  title: string;
  description: string;
};

type TourStepWithTarget<Events extends AnyTourEvents> = TourStepBase<Events> & {
  selector: string;
};

export type TourAdvanceAction = "open-first-trace";

export type TourStep<Events extends AnyTourEvents> =
  | (TourStepWithTarget<Events> & { type: "popover"; advanceAction?: TourAdvanceAction })
  | (TourStepWithTarget<Events> & { type: "task"; waitFor: keyof Events & string })
  | (TourStepBase<Events> & { type: "modal"; content?: string });

export type TourSection<Events extends AnyTourEvents> = {
  id: string;
  title: string;
  steps: TourStep<Events>[];
};

export type Tour<Events extends AnyTourEvents> = { id: string; sections: TourSection<Events>[] };
