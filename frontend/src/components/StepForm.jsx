import { fieldUI } from "../fields/registry";

// Renders any step by looping over its fields through the field registry.
export default function StepForm({ fields, values, onChange, disabled }) {
  if (!fields.length) return <p className="muted">This step has no fields. Submit it to continue.</p>;
  return fields.map((f) => {
    const { Editor, Viewer } = fieldUI(f.type);
    const id = `f-${f.key}`;
    return (
      <div className="field" key={f.id ?? f.key}>
        <label htmlFor={id}>{f.label}{f.required ? " *" : ""}</label>
        {disabled ? (
          <div>{values[f.key] != null ? <Viewer value={values[f.key]} /> : <span className="muted">Not filled in</span>}</div>
        ) : (
          <Editor id={id} field={f} value={values[f.key]} onChange={(v) => onChange(f.key, v)} />
        )}
      </div>
    );
  });
}
