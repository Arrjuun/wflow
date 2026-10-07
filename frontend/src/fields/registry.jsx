import { api } from "../api";

/* Frontend field-type registry. To add a type: add an entry here and a FieldType in backend/app/fields.py.
   Each entry: label, Editor (fill in), Viewer (read-only), optional ConfigEditor (workflow builder options). */

const Text = ({ id, field, value, onChange, type = "text", ...rest }) => (
  <input id={id} type={type} value={value ?? ""} maxLength={field.config?.max_length}
    onChange={(e) => onChange(e.target.value)} {...rest} />
);

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
    Editor: ({ id, value, onChange }) => <textarea id={id} value={value ?? ""} onChange={(e) => onChange(e.target.value)} />,
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
};

// Unknown types (added on the backend first) fall back to plain text instead of crashing.
export const fieldUI = (type) => FIELD_UI[type] || FIELD_UI.text;
