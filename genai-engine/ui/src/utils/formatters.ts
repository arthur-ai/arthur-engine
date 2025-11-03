const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "short",
  timeStyle: "short",
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
