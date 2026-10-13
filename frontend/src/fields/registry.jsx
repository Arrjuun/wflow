import { api } from "../api";

/* Frontend field-type registry. To add a type: add an entry here and a FieldType in backend/app/fields.py.
   Each entry: label, Editor (fill in), Viewer (read-only), optional ConfigEditor (workflow builder options). */

const Text = ({ id, field, value, onChange, type = "text", ...rest }) => (
  <input id={id} type={type} value={value ?? ""} maxLength={field.config?.max_length}
    placeholder={field.config?.placeholder || ""} onChange={(e) => onChange(e.target.value)} {...rest} />
);

function TableEditor({ id, field, value, onChange }) {
  const cols = field.config?.columns || [];
  const rows = value?.length ? value : [{}];
  const set = (i, key, v) => onChange(rows.map((r, j) => (j === i ? { ...r, [key]: v } : r)));
  return (
    <div className="table-field" id={id}>
      {rows.map((r, i) => (
        <div className="table-row" key={i} style={{ gridTemplateColumns: `repeat(${cols.length}, 1fr) auto` }}>
          {cols.map((c) => c.type === "dropdown" ? (
            <select key={c.key} aria-label={c.label} value={r[c.key] ?? ""} onChange={(e) => set(i, c.key, e.target.value)}>
              <option value="">{c.label}…</option>
              {c.options.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input key={c.key} aria-label={c.label} placeholder={c.label} type={c.type === "number" ? "number" : "text"}
              value={r[c.key] ?? ""} onChange={(e) => set(i, c.key, e.target.value)} />
          ))}
          <button type="button" className="btn danger small" aria-label="Remove row"
            onClick={() => onChange(rows.filter((_, j) => j !== i))}>Remove</button>
        </div>
      ))}
      <button type="button" className="btn secondary small" onClick={() => onChange([...rows, {}])}>Add row</button>
    </div>
  );
}

function TableViewer({ field, value }) {
  const cols = field.config?.columns || [];
  return (
    <div className="scroll-x"><table className="mini">
      <thead><tr>{cols.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
      <tbody>{value.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c.key}>{r[c.key]}</td>)}</tr>)}</tbody>
    </table></div>
  );
}

function ColumnsConfig({ config, onChange }) {
  const cols = config.columns || [];
  const set = (i, p) => onChange({ ...config, columns: cols.map((c, j) => (j === i ? { ...c, ...p } : c)) });
  return (
    <div>
      <label>Columns</label>
      {cols.map((c, i) => (
        <div className="row" key={i} style={{ marginBottom: 6 }}>
          <input aria-label="Column label" placeholder="Column label" value={c.label}
            onChange={(e) => set(i, { label: e.target.value, key: e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || c.key })} />
          <select aria-label="Column type" value={c.type} onChange={(e) => set(i, { type: e.target.value })}>
            <option value="text">Text</option><option value="dropdown">Drop-down</option><option value="number">Number</option>
          </select>
          {c.type === "dropdown" && <input aria-label="Options" placeholder="Options, comma separated" value={(c.options || []).join(",")}
            onChange={(e) => set(i, { options: e.target.value.split(",") })} />}
          <button type="button" className="btn danger small" style={{ flex: "0 0 auto" }}
            onClick={() => onChange({ ...config, columns: cols.filter((_, j) => j !== i) })}>Remove</button>
        </div>
      ))}
      <button type="button" className="btn secondary small"
        onClick={() => onChange({ ...config, columns: [...cols, { key: `col_${cols.length + 1}`, label: "", type: "text" }] })}>Add column</button>
    </div>
  );
}

function HeadingConfig({ config, onChange }) {
  return (
    <div><label>Text under the heading (optional)</label>
      <textarea value={config.text || ""} onChange={(e) => onChange({ ...config, text: e.target.value })} /></div>
  );
}

function FileEditor({ id, value, onChange }) {
  const pick = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      onChange(await api.upload(file));
    } catch (err) {
      alert(err.message);
    }
  };
  return (
    <div>
      <input id={id} type="file" onChange={pick} />
      {value && <div className="small muted">Attached: {value.name}</div>}
    </div>
  );
}

const FileViewer = ({ value }) => <a href={`/api/v1/files/${value.file_id}`}>{value.name}</a>;

function OptionsConfig({ config, onChange }) {
  return (
    <div>
      <label>Options (one per line)</label>
      <textarea value={(config.options || []).join("\n")}
        onChange={(e) => onChange({ ...config, options: e.target.value.split("\n") })} />
    </div>
  );
}

function RangeConfig({ config, onChange }) {
  return (
    <div className="row">
      {["min", "max"].map((k) => (
        <div key={k}>
          <label>{k === "min" ? "Minimum" : "Maximum"} (optional)</label>
          <input type="number" value={config[k] ?? ""} onChange={(e) => onChange({ ...config, [k]: e.target.value })} />
        </div>
      ))}
    </div>
  );
}

function FileConfig({ config, onChange }) {
  return (
    <div>
      <label>Allowed extensions (optional, comma separated)</label>
      <input value={(config.accept || []).join(", ")} placeholder="pdf, docx"
        onChange={(e) => onChange({ ...config, accept: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} />
    </div>
  );
}

export const FIELD_UI = {
  text: { label: "Short text (title)", Editor: Text, Viewer: ({ value }) => <>{value}</> },
  textarea: {
    label: "Long text (description)",
    Editor: ({ id, field, value, onChange }) => (
      <textarea id={id} value={value ?? ""} placeholder={field.config?.placeholder || ""} onChange={(e) => onChange(e.target.value)} />
    ),
    Viewer: ({ value }) => <div style={{ whiteSpace: "pre-wrap" }}>{value}</div>,
  },
  dropdown: {
    label: "Drop-down",
    Editor: ({ id, field, value, onChange }) => (
      <select id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select…</option>
        {(field.config?.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    ),
    Viewer: ({ value }) => <>{value}</>,
    ConfigEditor: OptionsConfig,
  },
  date: { label: "Date", Editor: (p) => <Text {...p} type="date" />, Viewer: ({ value }) => <>{value}</> },
  url: {
    label: "URL",
    Editor: (p) => <Text {...p} type="url" placeholder="https://" />,
    Viewer: ({ value }) => <a href={value} target="_blank" rel="noreferrer">{value}</a>,
  },
  number: {
    label: "Number",
    Editor: (p) => <Text {...p} type="number" value={p.value ?? ""} onChange={(v) => p.onChange(v === "" ? "" : Number(v))} />,
    Viewer: ({ value }) => <>{value}</>,
    ConfigEditor: RangeConfig,
  },
  file: { label: "File upload", Editor: FileEditor, Viewer: FileViewer, ConfigEditor: FileConfig },
  table: { label: "Table (repeating rows)", Editor: TableEditor, Viewer: TableViewer, ConfigEditor: ColumnsConfig, wide: true },
  heading: { label: "Section heading", display: true, ConfigEditor: HeadingConfig },
};

// Types that can be tested by a path condition between phases.
export const CONDITIONABLE = ["text", "textarea", "dropdown", "date", "url", "number"];

// Unknown types (added on the backend first) fall back to plain text instead of crashing.
export const fieldUI = (type) => FIELD_UI[type] || FIELD_UI.text;
