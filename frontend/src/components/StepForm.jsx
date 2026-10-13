import { fieldUI } from "../fields/registry";

// Splits fields into sections at each "heading" field, then lays them out on a two-column grid.
function sections(fields) {
  const out = [{ heading: null, fields: [] }];
  for (const f of fields) {
    if (f.type === "heading") out.push({ heading: f, fields: [] });
    else out[out.length - 1].fields.push(f);
  }
  return out.filter((s) => s.heading || s.fields.length);
}

function FieldCell({ f, value, onChange, disabled }) {
  const ui = fieldUI(f.type);
  const id = `f-${f.key}`;
  const half = f.config?.width === "half" && !ui.wide;
  return (
    <div className={`field ${half ? "half" : "full"}`}>
      <label htmlFor={id}>{f.label}{f.required ? " *" : ""}</label>
      {f.config?.help && <div className="hint">{f.config.help}</div>}
      {disabled
        ? <div className="readonly">{value != null && value !== "" ? <ui.Viewer field={f} value={value} /> : <span className="muted">Not filled in</span>}</div>
        : <ui.Editor id={id} field={f} value={value} onChange={(v) => onChange(f.key, v)} />}
    </div>
  );
}

export default function StepForm({ fields, values, onChange, disabled }) {
  if (!fields.length) return <p className="muted">This step has no fields.</p>;
  return sections(fields).map((sec, i) => {
    const grid = (
      <div className="form-grid">
        {sec.fields.map((f) => <FieldCell key={f.key} f={f} value={values[f.key]} onChange={onChange} disabled={disabled} />)}
      </div>
    );
    return sec.heading ? (
      <section className="group" key={i}>
        <h3>{sec.heading.label}</h3>
        {sec.heading.config?.text && <p className="muted">{sec.heading.config.text}</p>}
        {grid}
      </section>
    ) : <div key={i}>{grid}</div>;
  });
}
