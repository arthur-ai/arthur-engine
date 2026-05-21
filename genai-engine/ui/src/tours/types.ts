export type AnyTourEvents = Record<string, unknown>;

type TourStepBase<Events extends AnyTourEvents> = {
  id: string;
  route: string;
  routeParams?: Record<string, string>;
  selector: string;
  title: string;
  description: string;
};

export type TourStep<Events extends AnyTourEvents> =
  | (TourStepBase<Events> & { type: "popover" })
  | (TourStepBase<Events> & { type: "task"; waitFor: keyof Events & string });

export type TourSection<Events extends AnyTourEvents> = {
  id: string;
  title: string;
  steps: TourStep<Events>[];
};

export type Tour<Events extends AnyTourEvents> = { id: string; sections: TourSection<Events>[] };
