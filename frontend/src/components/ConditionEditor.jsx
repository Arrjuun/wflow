const OPS = [
  ["eq", "is"], ["ne", "is not"], ["gt", ">"], ["gte", "≥"], ["lt", "<"], ["lte", "≤"],
  ["in", "is one of"], ["contains", "contains"],
];

// value: null | { all: [{field, op, value}] }; fields: fields of the step the transition leaves
export default function ConditionEditor({ value, fields, onChange, disabled }) {
  const rules = value?.all || [];
  const set = (next) => onChange(next.length ? { all: next } : null);
  const update = (i, patch) => set(rules.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const display = (r) => (Array.isArray(r.value) ? r.value.join(", ") : r.value ?? "");

  return (
    <div>
      {rules.map((r, i) => (
        <div className="cond-row" key={i}>
          <select aria-label="Field" disabled={disabled} value={r.field} onChange={(e) => update(i, { field: e.target.value })}>
            <option value="">Field…</option>
            {fields.map((f) => <option key={f.key} value={f.key}>{f.label || f.key}</option>)}
          </select>
          <select aria-label="Operator" disabled={disabled} value={r.op} onChange={(e) => update(i, { op: e.target.value })}>
            {OPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input aria-label="Value" disabled={disabled} value={display(r)}
            placeholder={r.op === "in" ? "a, b, c" : "Value"}
            onChange={(e) => update(i, { value: r.op === "in" ? e.target.value.split(",").map((x) => x.trim()) : e.target.value })} />
          {!disabled && <button type="button" className="btn danger small" onClick={() => set(rules.filter((_, j) => j !== i))}>Remove</button>}
        </div>
      ))}
      {!rules.length && <div className="muted small">No condition. Add one, or mark this as the default path.</div>}
      {!disabled && (
        <button type="button" className="btn secondary small" disabled={!fields.length}
          onClick={() => set([...rules, { field: fields[0]?.key || "", op: "eq", value: "" }])}>
          Add condition
        </button>
      )}
    </div>
  );
}
