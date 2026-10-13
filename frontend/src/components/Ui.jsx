const TONE = {
  draft: "", pending_approval: "warn", approved: "ok", rejected: "bad", retired: "",
  active: "info", completed: "ok", archived: "", pending: "warn", disabled: "bad",
  in_progress: "info", submitted: "warn", in_review: "warn", awaiting_signoff: "warn", not_started: "",
};
const LABEL = { pending_approval: "pending approval", in_progress: "in progress", in_review: "in gate review", submitted: "awaiting approval",
  awaiting_signoff: "awaiting sign-off", not_started: "not started" };

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

export const Page = ({ children }) => <main className="page">{children}</main>;
export const ROLE_LABEL = { author: "Author (team)", approver: "Approver", authorizer: "Authorizer" };
