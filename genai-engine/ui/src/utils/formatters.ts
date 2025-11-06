import dayjs from "dayjs";
import duration from "dayjs/plugin/duration";

dayjs.extend(duration);

const { timeZone } = Intl.DateTimeFormat().resolvedOptions();

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "short",
  timeStyle: "long",
  timeZone,
});

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 5,
  maximumFractionDigits: 5,
});

export function formatDate(date: string | Date) {
  return dateFormatter.format(new Date(date));
}

export function formatCurrency(amount: number) {
  return currencyFormatter.format(amount);
}

export function formatDuration(duration: number) {
  return dayjs.duration(duration).format("HH:mm:ss");
}
