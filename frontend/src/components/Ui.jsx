const TONE = {
  draft: "", pending_approval: "warn", approved: "ok", rejected: "bad", retired: "",
  active: "info", completed: "ok", archived: "", pending: "warn", disabled: "bad",
  in_progress: "info", submitted: "warn",
};
const LABEL = { pending_approval: "pending approval", in_progress: "in progress" };

export const Chip = ({ value }) => (
  <span className={`chip ${TONE[value] ?? ""}`}>{LABEL[value] || value}</span>
);

export function Alert({ tone = "bad", children }) {
  if (!children || (Array.isArray(children) && !children.length)) return null;
  return <div className={`alert ${tone}`} role={tone === "bad" ? "alert" : "status"}>{children}</div>;
}

export function Errors({ error, errors }) {
  if (errors?.length) return <Alert><ul>{errors.map((e, i) => <li key={i}>{e}</li>)}</ul></Alert>;
  return <Alert>{error}</Alert>;
}

export const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "");
export const Empty = ({ children }) => <div className="empty">{children}</div>;
