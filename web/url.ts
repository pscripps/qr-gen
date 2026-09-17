const WEB_PROTOCOLS = new Set(["http:", "https:"]);
const DEFAULT_PROTOCOL = "https:";
const EXPLICIT_SCHEME = /^[a-z][a-z\d+.-]*:/i;
const HOST_WITH_PORT = /^[^/\s:]+:\d+(?:[/?#]|$)/;

export function normalizeUrl(input: string): string {
  const value = input.trim();
  if (!value) throw new Error("Paste a URL first.");
  if (/\s/.test(value))
    throw new Error(
      "Remove spaces or line breaks inside the URL, then try again.",
    );
  const hasScheme = EXPLICIT_SCHEME.test(value) && !HOST_WITH_PORT.test(value);
  const complete = value.startsWith("//")
    ? `${DEFAULT_PROTOCOL}${value}`
    : hasScheme
      ? value
      : `${DEFAULT_PROTOCOL}//${value}`;
  let parsed: URL;
  try {
    parsed = new URL(complete);
  } catch {
    throw new Error("Enter a website address, like google.com.");
  }
  if (!WEB_PROTOCOLS.has(parsed.protocol) || !parsed.hostname)
    throw new Error("Enter a website address, like google.com.");
  // Validate without reserializing: retain path, query, Unicode, and escaping.
  return complete;
}
