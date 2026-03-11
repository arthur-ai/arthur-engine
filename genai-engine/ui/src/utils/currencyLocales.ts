/**
 * Maps ISO 4217 currency codes to a BCP 47 locale where that currency is primary.
 * Use with Intl.NumberFormat(locale, { style: "currency", currency }) for correct
 * symbol placement and number formatting (e.g. €1.234,56 vs $1,234.56).
 */
export const CURRENCY_TO_LOCALE: Record<string, string> = {
  USD: "en-US",
  EUR: "de-DE",
  GBP: "en-GB",
  JPY: "ja-JP",
  CHF: "de-CH",
  CAD: "en-CA",
  AUD: "en-AU",
  CNY: "zh-CN",
  INR: "en-IN",
  KRW: "ko-KR",
  BRL: "pt-BR",
  MXN: "es-MX",
  ZAR: "en-ZA",
  HKD: "zh-HK",
  SGD: "en-SG",
  NOK: "nb-NO",
  SEK: "sv-SE",
  DKK: "da-DK",
  PLN: "pl-PL",
  THB: "th-TH",
  IDR: "id-ID",
  MYR: "ms-MY",
  PHP: "en-PH",
  CZK: "cs-CZ",
  ILS: "he-IL",
  CLP: "es-CL",
  COP: "es-CO",
  EGP: "ar-EG",
  NZD: "en-NZ",
  RON: "ro-RO",
  HUF: "hu-HU",
  TRY: "tr-TR",
  AED: "ar-AE",
  SAR: "ar-SA",
  RUB: "ru-RU",
  UAH: "uk-UA",
  VND: "vi-VN",
  PKR: "ur-PK",
  BGN: "bg-BG",
  HRK: "hr-HR",
  ISK: "is-IS",
};

/**
 * Return a BCP 47 locale for the given currency code for use with Intl.NumberFormat.
 * Unmapped codes fall back to "en-US".
 */
export function getLocaleForCurrency(currencyCode: string): string {
  const code = (currencyCode || "USD").trim().toUpperCase();
  return CURRENCY_TO_LOCALE[code] ?? "en-US";
}
