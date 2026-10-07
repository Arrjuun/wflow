import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";
import { clearInstance, decideInstance, fetchInstance, saveValues, submitInstance } from "../slices/tasksSlice";
import StepForm from "../components/StepForm";
import { Alert, Chip, Errors, fmt } from "../components/Ui";

export default function StepPage() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const { instance: inst, error, errors, busy, saved } = useSelector((s) => s.tasks);
  const [values, setValues] = useState({});
  const [comment, setComment] = useState("");

  useEffect(() => { dispatch(clearInstance()); dispatch(fetchInstance(id)); return () => { dispatch(clearInstance()); }; }, [dispatch, id]);
  useEffect(() => { if (inst) setValues(inst.values); }, [inst]);
  if (!inst || String(inst.id) !== id) return <Errors error={error} />;

  const change = (key, v) => setValues((cur) => ({ ...cur, [key]: v }));
  const history = inst.approvals.filter((a) => a.decision !== "pending");
  const pending = inst.approvals.filter((a) => a.decision === "pending" && a.round === inst.round);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{inst.step_key}. {inst.step_name}</h1>
          <p className="muted"><Link to={`/projects/${inst.project_id}`}>{inst.project_name}</Link> · assigned to {inst.assignee.name} · <Chip value={inst.status} />{inst.round > 1 ? ` · round ${inst.round}` : ""}</p>
        </div>
      </div>
      <Errors error={error} errors={errors} />
      {saved && !error && <Alert tone="ok">Saved</Alert>}
      {inst.round > 1 && inst.can_edit && history.length > 0 && (
        <Alert tone="warn">Sent back by {history[history.length - 1].user.name}: {history[history.length - 1].comment}</Alert>
      )}

      <div className="card">
        <StepForm fields={inst.fields} values={values} onChange={change} disabled={!inst.can_edit} />
        {inst.can_edit && (
          <div className="actions">
            <button className="btn secondary" disabled={busy} onClick={() => dispatch(saveValues({ id: inst.id, values }))}>Save draft</button>
            <button className="btn" disabled={busy} onClick={() => dispatch(submitInstance({ id: inst.id, values }))}>
              Submit
            </button>
          </div>
        )}
      </div>

      {inst.status === "submitted" && pending.length > 0 && (
        <p className="muted small">Waiting for: {pending.map((a) => a.user.name).join(", ")} ({inst.approval_policy === "all" ? "all must approve" : "any one approves"})</p>
      )}

      {inst.can_decide && (
        <div className="card">
          <h2>Your decision</h2>
          <div className="field"><label htmlFor="cm">Comment (required when sending back)</label>
            <textarea id="cm" value={comment} onChange={(e) => setComment(e.target.value)} /></div>
          <div className="actions">
            <button className="btn" disabled={busy} onClick={() => dispatch(decideInstance({ id: inst.id, decision: "approved", comment }))}>Approve</button>
            <button className="btn danger" disabled={busy} onClick={() => dispatch(decideInstance({ id: inst.id, decision: "rejected", comment }))}>Send back</button>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className="card">
          <h2>Review history</h2>
          <ul className="timeline">
            {history.map((a, i) => (
              <li key={i}><Chip value={a.decision === "approved" ? "approved" : "rejected"} /> <strong>{a.user.name}</strong>
                <span className="muted small">round {a.round} · {fmt(a.decided_at)}</span>{a.comment && <span>— {a.comment}</span>}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
