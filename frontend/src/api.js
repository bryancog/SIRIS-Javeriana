const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function buildUrl(path) {
  if (!path) return API_BASE_URL || "/";
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function exportUrl(path) {
  return buildUrl(path);
}

export async function apiFetch(path, options = {}) {
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {})
  };

  const response = await fetch(buildUrl(path), {
    credentials: "include",
    ...options,
    headers
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const backendMessage = payload?.message || payload?.detail?.message || payload?.detail || payload;
    throw new Error(typeof backendMessage === "string" ? backendMessage : "Error en la solicitud.");
  }

  return payload;
}
