export class ApiError extends Error {
  status: number;
  code: string;
  detail: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
export const TOKEN_KEY = "token";
/** sessionStorage key holding the BLACKLISTED message to show on /login. */
export const BLACKLIST_KEY = "collabz_blacklisted";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable */
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

type Params = Record<string, string | undefined>;

function buildUrl(path: string, params?: Params): string {
  const url = new URL(BASE_URL + path);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

interface RequestOptions {
  params?: Params;
  body?: unknown;
  form?: FormData;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

async function toError(res: Response, path: string): Promise<ApiError> {
  const text = await res.text();
  let parsed: unknown = undefined;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = undefined;
    }
  }
  let detail = res.statusText || "Request failed";
  let code = "ERROR";
  if (isRecord(parsed)) {
    if (typeof parsed.detail === "string") detail = parsed.detail;
    else if (parsed.detail !== undefined) detail = "Invalid request";
    if (typeof parsed.code === "string") code = parsed.code;
  }
  if (typeof window !== "undefined") {
    const isAuthCall = path.startsWith("/auth/login") || path.startsWith("/auth/register");
    const here = window.location.pathname;
    const onAuthPage = here === "/login" || here === "/register";
    if (res.status === 401 && !isAuthCall) {
      clearToken();
      if (!onAuthPage) window.location.assign("/login");
    } else if (code === "BLACKLISTED" && !isAuthCall) {
      clearToken();
      try {
        window.sessionStorage.setItem(BLACKLIST_KEY, detail);
      } catch {
        /* storage unavailable */
      }
      if (!onAuthPage) setTimeout(() => window.location.assign("/login"), 1500);
    }
  }
  return new ApiError(res.status, code, detail);
}

async function send(method: string, path: string, opts: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.params), { method, headers, body });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the server. Please try again.");
  }
  if (!res.ok) throw await toError(res, path);
  return res;
}

async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(method, path, opts);
  const text = await res.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    return undefined as T;
  }
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const api = {
  get<T>(path: string, params?: Params): Promise<T> {
    return request<T>("GET", path, { params });
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, { body });
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", path, { body });
  },
  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PUT", path, { body });
  },
  delete<T>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },
  upload<T>(path: string, form: FormData, method: string = "POST"): Promise<T> {
    return request<T>(method, path, { form });
  },
  async blob(path: string): Promise<Blob> {
    const res = await send("GET", path);
    return res.blob();
  },
  async download(path: string, filename: string): Promise<void> {
    const blob = await api.blob(path);
    saveBlob(blob, filename);
  },
};
