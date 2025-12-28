function getApiBase() {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // Client-side fallback: same host, port 8001 (Django dev)
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8001/api`;
  }
  // Server-side fallback for build tools
  return "http://127.0.0.1:8001/api";
}

export const API_BASE = getApiBase();

export type ApiResult<T> = { data: T; error?: string };

export async function apiGet<T>(path: string): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 30 },
      credentials: "include", // allow session auth
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      return { data: [] as unknown as T, error: res.statusText };
    }
    return { data: (await res.json()) as T };
  } catch (error: any) {
    return { data: [] as unknown as T, error: error.message };
  }
}
