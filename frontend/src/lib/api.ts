import type { Page } from "./types";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
function describe(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(describe).join(" ");
  if (value && typeof value === "object")
    return Object.entries(value)
      .map(
        ([key, val]) => `${key === "detail" ? "" : key + ": "}${describe(val)}`,
      )
      .join(" ");
  return "Не удалось выполнить запрос.";
}
async function raw<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (response.status === 204) return undefined as T;
  const data: unknown = await response
    .json()
    .catch(() => ({ detail: "Сервер временно недоступен." }));
  if (!response.ok) throw new ApiError(describe(data), response.status);
  return data as T;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    const session = await raw<{ csrfToken: string }>("/api/auth/session/");
    headers["X-CSRFToken"] = session.csrfToken;
  }
  const isFile = body instanceof FormData;
  if (body !== undefined && !isFile)
    headers["Content-Type"] = "application/json";
  return raw<T>(path, {
    method,
    headers,
    body: body === undefined ? undefined : isFile ? body : JSON.stringify(body),
  });
}
export async function all<T>(path: string): Promise<T[]> {
  let next: string | null = path;
  const rows: T[] = [];
  while (next) {
    const page: Page<T> = await api<Page<T>>(next);
    rows.push(...page.results);
    // Django pagination may carry the internal host; keep browser requests on this origin.
    if (page.next) {
      const url = new URL(page.next, window.location.origin);
      next = url.pathname + url.search;
    } else next = null;
  }
  return rows;
}
