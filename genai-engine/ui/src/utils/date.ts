const formatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "short",
  timeStyle: "short",
});

export function formatDate(date: string | Date) {
  return formatter.format(new Date(date));
}
