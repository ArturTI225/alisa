export function formatDateTime(value: string | Date, locale = "ro-RO", options?: Intl.DateTimeFormatOptions) {
  const date = typeof value === "string" ? new Date(value) : value;
  const formatter = new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    ...options,
  });
  return formatter.format(date);
}

const pluralRules = new Intl.PluralRules("ro");

export function formatPlural(count: number, forms: { one: string; few: string; other: string }) {
  const category = pluralRules.select(count);
  if (category === "one") return `${count} ${forms.one}`;
  if (category === "few") return `${count} ${forms.few}`;
  return `${count} ${forms.other}`;
}
