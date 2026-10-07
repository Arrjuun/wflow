import { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import {
  approveWorkflow, cloneWorkflow, clearCurrent, deleteWorkflow, fetchFieldTypes, fetchWorkflow,
  rejectWorkflow, retireWorkflow, saveWorkflow, submitWorkflow,
} from "../slices/workflowsSlice";
import ConditionEditor from "../components/ConditionEditor";
import { Alert, Chip, Errors } from "../components/Ui";
import { fieldUI } from "../fields/registry";

const slug = (s) => s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
const toDraft = (wf) => ({
  title: wf.title, description: wf.description,
  steps: wf.steps.map((s) => ({ key: s.key, name: s.name, is_start: s.is_start, is_terminal: s.is_terminal,
    approval_policy: s.approval_policy, fields: s.fields.map(({ key, type, label, required, config }) => ({ key, type, label, required, config })) })),
  transitions: wf.transitions.map(({ from_key, to_key, condition, priority, is_default }) => ({ from_key, to_key, condition, priority, is_default })),
});

export default function WorkflowBuilder() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { current: wf, fieldTypes, busy, error, errors } = useSelector((s) => s.workflows);
  const user = useSelector((s) => s.auth.user);
  const [draft, setDraft] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => { dispatch(clearCurrent()); dispatch(fetchWorkflow(id)); dispatch(fetchFieldTypes()); }, [dispatch, id]);
  useEffect(() => { if (wf && String(wf.id) === id) setDraft(toDraft(wf)); }, [wf, id]);

  const isOwner = wf && wf.owner?.id === user.id;
  const editable = wf && (isOwner || user.role === "admin") && ["draft", "rejected"].includes(wf.status);
  const isAdmin = user.role === "admin";
  const stepFields = useMemo(() => Object.fromEntries((draft?.steps || []).map((s) => [s.key, s.fields])), [draft]);

  if (!wf || !draft || String(wf.id) !== id) return <Errors error={error} />;

  const patch = (p) => setDraft((d) => ({ ...d, ...p }));
  const patchStep = (i, p) => patch({ steps: draft.steps.map((s, j) => (j === i ? { ...s, ...p } : s)) });
  const patchField = (i, k, p) => patchStep(i, { fields: draft.steps[i].fields.map((f, j) => (j === k ? { ...f, ...p } : f)) });
  const patchTrans = (i, p) => patch({ transitions: draft.transitions.map((t, j) => (j === i ? { ...t, ...p } : t)) });

  const addStep = () => {
    let n = draft.steps.length + 1;
    while (draft.steps.some((s) => s.key === String(n))) n++;
    patch({ steps: [...draft.steps, { key: String(n), name: `Step ${n}`, is_start: !draft.steps.length, is_terminal: false, approval_policy: "all", fields: [] }] });
  };
  const removeStep = (i) => {
    const key = draft.steps[i].key;
    patch({ steps: draft.steps.filter((_, j) => j !== i), transitions: draft.transitions.filter((t) => t.from_key !== key && t.to_key !== key) });
  };
  const setStart = (i) => patch({ steps: draft.steps.map((s, j) => ({ ...s, is_start: j === i })) });
  const renameKey = (i, newKey) => {
    const old = draft.steps[i].key;
    patch({
      steps: draft.steps.map((s, j) => (j === i ? { ...s, key: newKey } : s)),
      transitions: draft.transitions.map((t) => ({ ...t, from_key: t.from_key === old ? newKey : t.from_key, to_key: t.to_key === old ? newKey : t.to_key })),
    });
  };
  const addField = (i) => {
    const n = draft.steps[i].fields.length + 1;
    patchStep(i, { fields: [...draft.steps[i].fields, { key: `field_${n}`, type: "text", label: "", required: false, config: {} }] });
  };
  const addTransition = () => patch({ transitions: [...draft.transitions, { from_key: draft.steps[0]?.key || "", to_key: draft.steps[1]?.key || "", condition: null, priority: draft.transitions.length, is_default: false }] });

  const save = async () => {
    const res = await dispatch(saveWorkflow({ id: wf.id, data: draft }));
    if (saveWorkflow.fulfilled.match(res)) setMessage("Saved");
    return res;
  };
  const submit = async () => {
    const res = await save();
    if (!saveWorkflow.fulfilled.match(res)) return;
    const sub = await dispatch(submitWorkflow(wf.id));
    if (submitWorkflow.fulfilled.match(sub)) setMessage(user.role === "admin" ? "Submitted. You can approve it below." : "Submitted for admin approval");
  };
  const clone = async () => {
    const res = await dispatch(cloneWorkflow(wf.id));
    if (cloneWorkflow.fulfilled.match(res)) navigate(`/workflows/${res.payload.id}`);
  };
  const reject = () => {
    const comment = window.prompt("What should the owner change?");
    if (comment) dispatch(rejectWorkflow({ id: wf.id, comment }));
  };
  const remove = async () => {
    if (!window.confirm("Delete this workflow?")) return;
    const res = await dispatch(deleteWorkflow(wf.id));
    if (deleteWorkflow.fulfilled.match(res)) navigate("/workflows");
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{wf.title} <Chip value={wf.status} /></h1>
          <p className="muted">Version {wf.version} · owner {wf.owner?.name}</p>
        </div>
        <div className="actions">
          {editable && <>
            <button className="btn secondary" disabled={busy} onClick={save}>Save</button>
            <button className="btn" disabled={busy} onClick={submit}>Submit for approval</button>
            <button className="btn danger" disabled={busy} onClick={remove}>Delete</button>
          </>}
          {isAdmin && ["pending_approval", "draft", "rejected"].includes(wf.status) && <button className="btn" disabled={busy} onClick={() => dispatch(approveWorkflow(wf.id))}>Approve</button>}
          {isAdmin && wf.status === "pending_approval" && <button className="btn danger" disabled={busy} onClick={reject}>Reject</button>}
          {isAdmin && wf.status === "approved" && <button className="btn secondary" disabled={busy} onClick={() => dispatch(retireWorkflow(wf.id))}>Retire</button>}
          {!editable && <button className="btn secondary" disabled={busy} onClick={clone}>Clone to edit</button>}
        </div>
      </div>

      <Errors error={error} errors={errors} />
      {message && !error && !errors && <Alert tone="ok">{message}</Alert>}
      {wf.status === "rejected" && wf.review_comment && <Alert tone="warn">Rejected: {wf.review_comment}</Alert>}
      {wf.status === "pending_approval" && <Alert tone="warn">Waiting for admin approval. It cannot be edited until reviewed.</Alert>}
      {wf.status === "approved" && <Alert tone="ok">Approved workflows are read-only. Clone it to make changes as a new version.</Alert>}

      <div className="card">
        <div className="field"><label htmlFor="t">Title</label>
          <input id="t" disabled={!editable} value={draft.title} onChange={(e) => patch({ title: e.target.value })} /></div>
        <div className="field"><label htmlFor="d">Description</label>
          <textarea id="d" disabled={!editable} value={draft.description} onChange={(e) => patch({ description: e.target.value })} /></div>
      </div>

      <h2>Steps</h2>
      {draft.steps.map((s, i) => (
        <div key={i} className={`step-card ${s.is_start ? "start" : s.is_terminal ? "end" : ""}`}>
          <div className="row">
            <div style={{ flex: "0 0 90px" }}><label>Key</label>
              <input disabled={!editable} value={s.key} onChange={(e) => renameKey(i, e.target.value)} /></div>
            <div style={{ flex: "2 1 220px" }}><label>Step name</label>
              <input disabled={!editable} value={s.name} onChange={(e) => patchStep(i, { name: e.target.value })} /></div>
            <div><label>Approval</label>
              <select disabled={!editable} value={s.approval_policy} onChange={(e) => patchStep(i, { approval_policy: e.target.value })}>
                <option value="all">All approvers must approve</option><option value="any">Any one approver</option>
              </select></div>
          </div>
          <div className="actions" style={{ margin: "10px 0" }}>
            <label className="check"><input type="radio" name="start" disabled={!editable} checked={s.is_start} onChange={() => setStart(i)} /> Start step</label>
            <label className="check"><input type="checkbox" disabled={!editable} checked={s.is_terminal} onChange={(e) => patchStep(i, { is_terminal: e.target.checked })} /> End step</label>
            {editable && <button className="btn danger small" onClick={() => removeStep(i)}>Remove step</button>}
          </div>

          <h3>Fields</h3>
          {!s.fields.length && <p className="muted small">No fields. The assignee just submits the step.</p>}
          {s.fields.map((f, k) => {
            const { ConfigEditor } = fieldUI(f.type);
            return (
              <div className="field-row" key={k}>
                <div><label>Type</label>
                  <select disabled={!editable} value={f.type} onChange={(e) => patchField(i, k, { type: e.target.value, config: {} })}>
                    {fieldTypes.map((t) => <option key={t.name} value={t.name}>{fieldUI(t.name).label || t.label}</option>)}
                  </select></div>
                <div><label>Label</label>
                  <input disabled={!editable} value={f.label}
                    onChange={(e) => patchField(i, k, { label: e.target.value, key: slug(e.target.value) || f.key })} /></div>
                <div><label>Key (used in conditions)</label>
                  <input disabled={!editable} value={f.key} onChange={(e) => patchField(i, k, { key: slug(e.target.value) })} /></div>
                <label className="check"><input type="checkbox" disabled={!editable} checked={f.required} onChange={(e) => patchField(i, k, { required: e.target.checked })} /> Required</label>
                {editable && <button className="btn danger small" onClick={() => patchStep(i, { fields: s.fields.filter((_, j) => j !== k) })}>Remove</button>}
                {ConfigEditor && <div className="cfg"><fieldset disabled={!editable} style={{ border: 0, padding: 0, margin: 0 }}>
                  <ConfigEditor config={f.config || {}} onChange={(config) => patchField(i, k, { config })} /></fieldset></div>}
              </div>
            );
          })}
          {editable && <button className="btn secondary small" onClick={() => addField(i)}>Add field</button>}
        </div>
      ))}
      {editable && <button className="btn secondary" onClick={addStep}>Add step</button>}

      <h2 style={{ marginTop: 28 }}>Paths between steps</h2>
      <div className="card">
        <p className="muted small">After a step is approved, the first matching condition (lowest priority number first) decides the next step. The default path is used when none match.</p>
        {draft.transitions.map((t, i) => (
          <div className="trans-row" key={i}>
            <div><label>From</label>
              <select disabled={!editable} value={t.from_key} onChange={(e) => patchTrans(i, { from_key: e.target.value, condition: null })}>
                {draft.steps.map((s) => <option key={s.key} value={s.key}>{s.key}</option>)}</select></div>
            <div><label>To</label>
              <select disabled={!editable} value={t.to_key} onChange={(e) => patchTrans(i, { to_key: e.target.value })}>
                {draft.steps.map((s) => <option key={s.key} value={s.key}>{s.key}</option>)}</select></div>
            <div><label>Priority</label>
              <input type="number" disabled={!editable} value={t.priority} onChange={(e) => patchTrans(i, { priority: Number(e.target.value) })} /></div>
            <label className="check" style={{ marginTop: 22 }}><input type="checkbox" disabled={!editable} checked={t.is_default} onChange={(e) => patchTrans(i, { is_default: e.target.checked, condition: e.target.checked ? null : t.condition })} /> Default</label>
            <div>{t.is_default ? <span className="muted small">Used when no other condition matches.</span>
              : <ConditionEditor disabled={!editable} value={t.condition} fields={stepFields[t.from_key] || []} onChange={(condition) => patchTrans(i, { condition })} />}</div>
            {editable && <button className="btn danger small" style={{ marginTop: 22 }} onClick={() => patch({ transitions: draft.transitions.filter((_, j) => j !== i) })}>Remove</button>}
          </div>
        ))}
        {editable && <button className="btn secondary small" disabled={draft.steps.length < 2} onClick={addTransition}>Add path</button>}
      </div>
    </>
  );
}
