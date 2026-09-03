import type { ZodError } from "zod";

export function zodFieldErrors(error: ZodError): Record<string, string> {
  const result: Record<string, string> = {};

  for (const issue of error.issues) {
    const key = issue.path.length > 0 ? String(issue.path[0]) : "form";
    if (!(key in result)) {
      result[key] = issue.message;
    }
  }

  return result;
}
