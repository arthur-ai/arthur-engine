import { useBucketer } from "../../context/bucket-context";

import { DurationCell } from "./DurationCell";

import { formatDuration } from "@/utils/formatters";

type Props = {
  duration: number;
};

export const DurationCellWithBucket = ({ duration }: Props) => {
  const bucketer = useBucketer();
  return <DurationCell duration={duration} bucketer={bucketer} formatDuration={formatDuration} />;
};
