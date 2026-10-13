import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import {
  approveWorkflow, cloneWorkflow, clearCurrent, deleteWorkflow, fetchFieldTypes, fetchWorkflow,
  rejectWorkflow, retireWorkflow, saveWorkflow, submitWorkflow,
} from "../slices/workflowsSlice";
import ConditionEditor from "../components/ConditionEditor";
import { Alert, Chip, Errors, Page } from "../components/Ui";
import { CONDITIONABLE } from "../fields/registry";
import FieldDefEditor from "../components/FieldDefEditor";

const toDraft = (wf) => ({
  title: wf.title, description: wf.description,
  phases: wf.phases.map((p) => ({
    key: p.key, name: p.name, is_start: p.is_start, is_terminal: p.is_terminal, requires_gate: p.requires_gate,
    steps: p.steps.map((s) => ({ name: s.name, fields: s.fields.map(({ key, type, label, required, config }) => ({ key, type, label, required, config })) })),
  })),
  transitions: wf.transitions.map(({ from_key, to_key, condition, is_default }) => ({ from_key, to_key, condition, is_default })),
});

export default function WorkflowBuilder() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { current: wf, fieldTypes, busy, error, errors } = useSelector((s) => s.workflows);
  const user = useSelector((s) => s.auth.user);
  const [draft, setDraft] = useState(null);
  const [open, setOpen] = useState(0);
  const [message, setMessage] = useState("");

  useEffect(() => { dispatch(clearCurrent()); dispatch(fetchWorkflow(id)); dispatch(fetchFieldTypes()); }, [dispatch, id]);
  useEffect(() => { if (wf && String(wf.id) === id) setDraft(toDraft(wf)); }, [wf, id]);

  if (!wf || !draft || String(wf.id) !== id) return <Page><Errors error={error} /></Page>;

  const isAdmin = user.role === "admin";
  const editable = (wf.owner?.id === user.id || isAdmin) && ["draft", "rejected"].includes(wf.status);
  const patch = (p) => setDraft((d) => ({ ...d, ...p }));
  const patchPhase = (i, p) => setDraft((d) => ({ ...d, phases: d.phases.map((ph, j) => (j === i ? { ...ph, ...p } : ph)) }));
  const patchStep = (i, k, p) => patchPhase(i, { steps: draft.phases[i].steps.map((s, j) => (j === k ? { ...s, ...p } : s)) });
  const patchField = (i, k, n, p) => patchStep(i, k, { fields: draft.phases[i].steps[k].fields.map((f, j) => (j === n ? { ...f, ...p } : f)) });
  const patchPath = (i, p) => patch({ transitions: draft.transitions.map((t, j) => (j === i ? { ...t, ...p } : t)) });

  const addPhase = () => {
    let n = draft.phases.length + 1;
    while (draft.phases.some((p) => p.key === String(n))) n++;
    patch({ phases: [...draft.phases, { key: String(n), name: "New phase", is_start: !draft.phases.length, is_terminal: false, requires_gate: true,
      steps: [{ name: "New step", fields: [] }] }] });
    setOpen(draft.phases.length);
  };
  const removePhase = (i) => {
    const key = draft.phases[i].key;
    patch({ phases: draft.phases.filter((_, j) => j !== i), transitions: draft.transitions.filter((t) => t.from_key !== key && t.to_key !== key) });
  };
  const movePhase = (i, d) => {
    const ps = [...draft.phases];
    [ps[i], ps[i + d]] = [ps[i + d], ps[i]];
    patch({ phases: ps });
    setOpen(i + d);
  };
  const renameKey = (i, newKey) => {
    const old = draft.phases[i].key;
    patch({
      phases: draft.phases.map((p, j) => (j === i ? { ...p, key: newKey } : p)),
      transitions: draft.transitions.map((t) => ({ ...t, from_key: t.from_key === old ? newKey : t.from_key, to_key: t.to_key === old ? newKey : t.to_key })),
    });
  };
  const addStep = (i) => patchPhase(i, { steps: [...draft.phases[i].steps, { name: "New step", fields: [] }] });
  const addField = (i, k) => {
    const n = draft.phases[i].steps.reduce((c, s) => c + s.fields.length, 0) + 1;
    patchStep(i, k, { fields: [...draft.phases[i].steps[k].fields, { key: `field_${n}`, type: "text", label: "", required: false, config: { width: "full" } }] });
  };
  const linkInOrder = () => {
    const ps = draft.phases;
    patch({ transitions: ps.slice(0, -1).filter((p) => !p.is_terminal).map((p, i) => ({ from_key: p.key, to_key: ps[i + 1].key, condition: null, is_default: false })) });
  };
  const pathFields = (fromKey) => (draft.phases.find((p) => p.key === fromKey)?.steps || [])
    .flatMap((s) => s.fields).filter((f) => CONDITIONABLE.includes(f.type));
  const outCount = (key) => draft.transitions.filter((t) => t.from_key === key).length;

  const save = async () => {
    const res = await dispatch(saveWorkflow({ id: wf.id, data: draft }));
    if (saveWorkflow.fulfilled.match(res)) setMessage("Saved");
    return res;
  };
  const submit = async () => {
    if (!saveWorkflow.fulfilled.match(await save())) return;
    if (submitWorkflow.fulfilled.match(await dispatch(submitWorkflow(wf.id)))) setMessage(isAdmin ? "Submitted. You can approve it now." : "Submitted for admin approval");
  };
  const clone = async () => {
    const res = await dispatch(cloneWorkflow(wf.id));
    if (cloneWorkflow.fulfilled.match(res)) navigate(`/workflows/${res.payload.id}`);
  };
  const reject = () => { const c = window.prompt("What should the owner change?"); if (c) dispatch(rejectWorkflow({ id: wf.id, comment: c })); };
  const remove = async () => {
    if (!window.confirm("Delete this workflow?")) return;
    if (deleteWorkflow.fulfilled.match(await dispatch(deleteWorkflow(wf.id)))) navigate("/workflows");
  };

  return (
    <Page>
      <div className="page-head">
        <div><h1>{wf.title} <Chip value={wf.status} /></h1><p className="muted">Version {wf.version}, owner {wf.owner?.name}</p></div>
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

      <section className="card">
        <div className="field"><label htmlFor="t">Title</label><input id="t" disabled={!editable} value={draft.title} onChange={(e) => patch({ title: e.target.value })} /></div>
        <div className="field"><label htmlFor="d">Description</label><textarea id="d" disabled={!editable} value={draft.description} onChange={(e) => patch({ description: e.target.value })} /></div>
      </section>

      <h2>Phases</h2>
      <p className="muted small">A workflow is a sequence of phases. Each phase has steps (shown as tabs) with fields, and ends in a gate review by the project's approvers and authorizers.</p>
      {draft.phases.map((p, i) => (
        <div key={i} className={`phase-card ${p.is_start ? "start" : p.is_terminal ? "end" : ""}`}>
          <button type="button" className="phase-toggle" aria-expanded={open === i} onClick={() => setOpen(open === i ? -1 : i)}>
            <span>{p.key}</span> {p.name || "Untitled phase"}
            <span className="muted small"> {p.steps.length} step{p.steps.length === 1 ? "" : "s"}{p.is_start ? ", start" : ""}{p.is_terminal ? ", end" : ""}{p.requires_gate ? "" : ", no gate"}</span>
          </button>
          {open === i && (
            <div className="phase-body">
              <div className="row">
                <div style={{ flex: "0 0 90px" }}><label>Key</label><input disabled={!editable} value={p.key} onChange={(e) => renameKey(i, e.target.value)} /></div>
                <div style={{ flex: "3 1 260px" }}><label>Phase name</label><input disabled={!editable} value={p.name} onChange={(e) => patchPhase(i, { name: e.target.value })} /></div>
              </div>
              <div className="actions" style={{ margin: "10px 0 14px" }}>
                <label className="check"><input type="radio" name="start" disabled={!editable} checked={p.is_start} onChange={() => patch({ phases: draft.phases.map((x, j) => ({ ...x, is_start: j === i })) })} /> Start phase</label>
                <label className="check"><input type="checkbox" disabled={!editable} checked={p.is_terminal} onChange={(e) => patchPhase(i, { is_terminal: e.target.checked })} /> End phase</label>
                <label className="check"><input type="checkbox" disabled={!editable} checked={p.requires_gate} onChange={(e) => patchPhase(i, { requires_gate: e.target.checked })} /> Gate review</label>
                {editable && <>
                  <button className="btn secondary small" disabled={i === 0} onClick={() => movePhase(i, -1)}>Move up</button>
                  <button className="btn secondary small" disabled={i === draft.phases.length - 1} onClick={() => movePhase(i, 1)}>Move down</button>
                  <button className="btn danger small" onClick={() => removePhase(i)}>Remove phase</button>
                </>}
              </div>
              {p.steps.map((s, k) => (
                <div className="step-card" key={k}>
                  <div className="row" style={{ alignItems: "flex-end" }}>
                    <div style={{ flex: "3 1 260px" }}><label>Step name (tab)</label><input disabled={!editable} value={s.name} onChange={(e) => patchStep(i, k, { name: e.target.value })} /></div>
                    {editable && <div style={{ flex: "0 0 auto" }}><button className="btn danger small" onClick={() => patchPhase(i, { steps: p.steps.filter((_, j) => j !== k) })}>Remove step</button></div>}
                  </div>
                  {!s.fields.length && <p className="muted small">No fields yet.</p>}
                  {s.fields.map((f, n) => (
                    <FieldDefEditor key={n} f={f} fieldTypes={fieldTypes} editable={editable}
                      onChange={(fp) => patchField(i, k, n, fp)}
                      onRemove={() => patchStep(i, k, { fields: s.fields.filter((_, j) => j !== n) })} />
                  ))}
                  {editable && <button className="btn secondary small" onClick={() => addField(i, k)}>Add field</button>}
                </div>
              ))}
              {editable && <button className="btn secondary small" onClick={() => addStep(i)}>Add step</button>}
            </div>
          )}
        </div>
      ))}
      {editable && <button className="btn secondary" onClick={addPhase}>Add phase</button>}

      <h2 style={{ marginTop: 28 }}>Paths between phases</h2>
      <section className="card">
        <p className="muted small">
          After a phase passes its gate review, the project moves along its path. For a branch, add one path with a condition and one marked default:
          the condition is checked first, and the default is taken when it does not match. Conditions can use the fields of the phase being left.
        </p>
        {editable && <button className="btn secondary small" style={{ marginBottom: 10 }} disabled={draft.phases.length < 2} onClick={linkInOrder}>Link phases in order</button>}
        {draft.transitions.map((t, i) => (
          <div className="path-row" key={i}>
            <div><label>From</label><select disabled={!editable} value={t.from_key} onChange={(e) => patchPath(i, { from_key: e.target.value, condition: null })}>
              {draft.phases.map((p) => <option key={p.key} value={p.key}>{p.name || p.key}</option>)}</select></div>
            <div><label>To</label><select disabled={!editable} value={t.to_key} onChange={(e) => patchPath(i, { to_key: e.target.value })}>
              {draft.phases.map((p) => <option key={p.key} value={p.key}>{p.name || p.key}</option>)}</select></div>
            <div>
              {outCount(t.from_key) > 1 ? (
                <>
                  <label className="check" style={{ marginBottom: 6 }}><input type="checkbox" disabled={!editable} checked={t.is_default}
                    onChange={(e) => patchPath(i, { is_default: e.target.checked, condition: e.target.checked ? null : t.condition })} /> Default (taken when the condition does not match)</label>
                  {!t.is_default && <ConditionEditor disabled={!editable} value={t.condition} fields={pathFields(t.from_key)} onChange={(condition) => patchPath(i, { condition })} />}
                </>
              ) : <span className="muted small">Only path from this phase, always taken.</span>}
            </div>
            {editable ? <button className="btn danger small" onClick={() => patch({ transitions: draft.transitions.filter((_, j) => j !== i) })}>Remove</button> : <div />}
          </div>
        ))}
        {editable && <button className="btn secondary small" disabled={draft.phases.length < 2}
          onClick={() => patch({ transitions: [...draft.transitions, { from_key: draft.phases[0].key, to_key: draft.phases[1].key, condition: null, is_default: false }] })}>Add path</button>}
      </section>
    </Page>
  );
}
