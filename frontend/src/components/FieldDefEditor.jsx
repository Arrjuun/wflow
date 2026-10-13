import { fieldUI } from "../fields/registry";

export const slug = (s) => s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

// Edits one field definition: type, label, key, width, required, placeholder and type options.
export default function FieldDefEditor({ f, fieldTypes, editable = true, onChange, onRemove }) {
  const { ConfigEditor, display } = fieldUI(f.type);
  const cfg = f.config || {};
  const setCfg = (p) => onChange({ config: { ...cfg, ...p } });
  return (
    <div className="field-row">
      <div><label>Type</label>
        <select disabled={!editable} value={f.type} onChange={(e) => onChange({ type: e.target.value, config: { width: cfg.width } })}>
          {fieldTypes.map((t) => <option key={t.name} value={t.name}>{fieldUI(t.name).label || t.label}</option>)}
        </select></div>
      <div><label>Label</label>
        <input disabled={!editable} value={f.label} onChange={(e) => onChange({ label: e.target.value, key: slug(e.target.value) || f.key })} /></div>
      <div><label>Key</label>
        <input disabled={!editable} value={f.key} onChange={(e) => onChange({ key: slug(e.target.value) })} /></div>
      {!display ? (
        <div><label>Width</label>
          <select disabled={!editable} value={cfg.width || "full"} onChange={(e) => setCfg({ width: e.target.value })}>
            <option value="full">Full row</option><option value="half">Half row</option>
          </select></div>
      ) : <div />}
      {!display ? <label className="check"><input type="checkbox" disabled={!editable} checked={!!f.required} onChange={(e) => onChange({ required: e.target.checked })} /> Required</label> : <div />}
      {editable ? <button type="button" className="btn danger small" onClick={onRemove}>Remove</button> : <div />}
      <fieldset className="cfg" disabled={!editable}>
        {!display && ["text", "textarea", "url", "number"].includes(f.type) && (
          <div><label>Placeholder (optional)</label><input value={cfg.placeholder || ""} onChange={(e) => setCfg({ placeholder: e.target.value })} /></div>
        )}
        {ConfigEditor && <ConfigEditor config={cfg} onChange={(config) => onChange({ config })} />}
      </fieldset>
    </div>
  );
}
