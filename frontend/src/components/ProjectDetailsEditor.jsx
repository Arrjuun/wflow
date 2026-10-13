import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchFieldTypes } from "../slices/workflowsSlice";
import FieldDefEditor from "./FieldDefEditor";
import StepForm from "./StepForm";

/* The project creator defines the project's own detail fields (FEM number, start date, anything)
   and fills them in. value: { name, detail_fields: [...], detail_values: {...} } */
export default function ProjectDetailsEditor({ value, onChange }) {
  const dispatch = useDispatch();
  const fieldTypes = useSelector((s) => s.workflows.fieldTypes);
  useEffect(() => { if (!fieldTypes.length) dispatch(fetchFieldTypes()); }, [dispatch, fieldTypes.length]);

  const fields = value.detail_fields;
  const setFields = (detail_fields) => onChange({ ...value, detail_fields });
  const add = () => {
    let n = fields.length + 1;
    while (fields.some((f) => f.key === `detail_${n}`)) n++;
    setFields([...fields, { key: `detail_${n}`, type: "text", label: "", required: false, config: { width: "half" } }]);
  };

  return (
    <>
      <div className="field"><label htmlFor="pname">Project name</label>
        <input id="pname" required value={value.name} onChange={(e) => onChange({ ...value, name: e.target.value })} /></div>

      <h3>Detail fields</h3>
      <p className="muted small">Add whatever this project needs, for example a start date or a FEM registration number.</p>
      {fields.map((f, i) => (
        <FieldDefEditor key={i} f={f} fieldTypes={fieldTypes}
          onChange={(p) => setFields(fields.map((x, j) => (j === i ? { ...x, ...p } : x)))}
          onRemove={() => setFields(fields.filter((_, j) => j !== i))} />
      ))}
      <button type="button" className="btn secondary small" onClick={add}>Add detail field</button>

      {fields.some((f) => f.type !== "heading") && (
        <div className="group" style={{ marginTop: 18 }}>
          <h3>Values</h3>
          <StepForm fields={fields} values={value.detail_values}
            onChange={(k, v) => onChange({ ...value, detail_values: { ...value.detail_values, [k]: v } })} />
        </div>
      )}
    </>
  );
}
