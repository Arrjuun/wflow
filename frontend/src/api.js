const BASE = "/api/v1";

function messageFrom(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || String(d)).join("; ");
  if (detail.errors) return detail.errors.join("; ");
  return fallback;
}

export class ApiError extends Error {
  constructor(status, detail, fallback) {
    super(messageFrom(detail, fallback));
    this.status = status;
    this.errors = detail?.errors || null;
  }
}

async function request(path, { method = "GET", body, form } = {}) {
  const opts = { method, credentials: "include", headers: {} };
  if (form) opts.body = form;
  else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, opts);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data?.detail, res.statusText || "Request failed");
  return data;
}

export const api = {
  get: (p) => request(p),
  post: (p, body = {}) => request(p, { method: "POST", body }),
  put: (p, body) => request(p, { method: "PUT", body }),
  patch: (p, body) => request(p, { method: "PATCH", body }),
  del: (p) => request(p, { method: "DELETE" }),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/files", { method: "POST", form });
  },
};
