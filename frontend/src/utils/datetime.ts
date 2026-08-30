const BEIJING_TIME_ZONE = "Asia/Shanghai";

const beijingDateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: BEIJING_TIME_ZONE,
  calendar: "gregory",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

/**
 * Format an ISO timestamp as Beijing time, independent of the browser's local timezone.
 *
 * API timestamps are expected to be UTC ISO values. Legacy timezone-less values
 * are treated as Asia/Shanghai; ISO values with an explicit offset are respected.
 */
export function formatBeijingTime(value: string | null | undefined): string {
  if (!value) return "—";

  const iso = value.trim();
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso);
  const date = new Date(hasTimezone ? iso : `${iso}+08:00`);
  if (Number.isNaN(date.getTime())) return value;

  const parts = Object.fromEntries(
    beijingDateTimeFormatter.formatToParts(date).map(({ type, value: part }) => [
      type,
      part,
    ]),
  );
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
}
