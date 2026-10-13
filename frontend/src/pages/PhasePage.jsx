import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { clearInstance, decideStep, fetchInstance, saveValues, submitStep } from "../slices/phasesSlice";
import { fetchProject } from "../slices/projectsSlice";
import StepForm from "../components/StepForm";
import { Alert, Chip, Errors, fmt } from "../components/Ui";

export function usePhaseInstance() {
  const { id, key } = useParams();
  const dispatch = useDispatch();
  const project = useSelector((s) => s.projects.current);
  const phase = project?.phases.find((ph) => ph.key === key);
  const state = useSelector((s) => s.phases);
  useEffect(() => {
    dispatch(clearInstance());
    if (phase?.instance_id) dispatch(fetchInstance(phase.instance_id));
  }, [dispatch, phase?.instance_id]);
  const inst = state.instance && state.instance.id === phase?.instance_id ? state.instance : null;
  return { id, key, project, phase, inst, ...state };
}

const MARK = { approved: "✓ ", submitted: "◷ " };

function Review({ step, busy, onDecide }) {
  const [comment, setComment] = useState("");
  return (
    <section className="card decision">
      <h2>Review this step</h2>
      <div className="field"><label htmlFor="cm">Comment (required when sending back)</label>
        <textarea id="cm" value={comment} onChange={(e) => setComment(e.target.value)} /></div>
      <div className="actions">
        <button className="btn" disabled={busy} onClick={() => onDecide(step.id, "approved", comment).then(() => setComment(""))}>Approve step</button>
        <button className="btn danger" disabled={busy} onClick={() => onDecide(step.id, "rejected", comment).then(() => setComment(""))}>Send back to team</button>
      </div>
    </section>
  );
}

export default function PhasePage() {
  const dispatch = useDispatch();
  const [params] = useSearchParams();
  const { id, key, project, phase, inst, error, errors, busy, notice } = usePhaseInstance();
  const [tab, setTab] = useState(0);
  const [values, setValues] = useState({});
  useEffect(() => { if (inst) setValues(inst.values); }, [inst]);
  useEffect(() => {  // open the step linked from "My work", otherwise the first one
    const wanted = Number(params.get("step"));
    const i = inst?.steps.findIndex((s) => s.id === wanted) ?? -1;
    setTab(i >= 0 ? i : 0);
  }, [key, params, inst?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!phase) return <Errors error="This phase does not exist in the project's workflow." />;
  if (!phase.instance_id) return (
    <>
      <h1>{phase.name}</h1>
      <div className="card"><p className="muted">
        {project.status === "active" ? "This phase opens after the previous phase is signed off, if the project's path leads here." : "This phase was not part of the path this project took."}
      </p></div>
    </>
  );
  if (!inst) return <Errors error={error} />;

  const step = inst.steps[Math.min(tab, inst.steps.length - 1)];
  const refresh = (res) => { if (!res.error) dispatch(fetchProject(id)); return res; };
  const decide = (stepId, decision, comment) => dispatch(decideStep({ stepId, decision, comment })).then(refresh);
  const pending = step.status === "submitted"
    ? inst.approvers.filter((u) => !step.decisions.some((d) => d.round === step.round && d.user.id === u.id))
    : [];
  const sentBack = step.status === "in_progress" && step.round > 1 ? [...step.decisions].reverse().find((d) => d.decision === "rejected") : null;

  return (
    <>
      <div className="page-head"><h1>{phase.name}</h1><Chip value={inst.status} /></div>
      <Errors error={error} errors={errors} />
      <Alert tone="ok">{notice}</Alert>
      {inst.status === "awaiting_signoff" && (
        <Alert tone="warn">All steps are approved. Waiting for the authorizer: <Link to={`/projects/${id}/phases/${key}/gate`}>open gate review</Link></Alert>
      )}

      <div className="tabs" role="tablist">
        {inst.steps.map((s, i) => (
          <button key={s.id} role="tab" aria-selected={i === tab} className={i === tab ? "active" : ""} onClick={() => setTab(i)}>
            {MARK[s.status] || ""}{s.name}
          </button>
        ))}
      </div>
      <div className="card tab-panel">
        <div className="step-status">
          <Chip value={step.status} />
          {step.round > 1 && <span className="muted small">Round {step.round}</span>}
          {pending.length > 0 && <span className="muted small">Waiting for {pending.map((u) => u.name).join(", ")}</span>}
        </div>
        {sentBack && <Alert tone="warn">Sent back by {sentBack.user.name}: {sentBack.comment}</Alert>}
        <StepForm fields={step.fields} values={values} onChange={(k, v) => setValues((c) => ({ ...c, [k]: v }))} disabled={!step.can_edit} />
        {step.can_edit && (
          <div className="actions">
            <button className="btn secondary" disabled={busy} onClick={() => dispatch(saveValues({ id: inst.id, values }))}>Save draft</button>
            <button className="btn" disabled={busy} onClick={() => dispatch(submitStep({ stepId: step.id, values })).then(refresh)}>Submit step for approval</button>
          </div>
        )}
        {!step.can_edit && step.status === "in_progress" && project.status === "active" && !inst.is_author && (
          <p className="muted small">Only the project team (authors) or an admin can fill in and submit this step.</p>
        )}
      </div>

      {step.can_decide && <Review step={step} busy={busy} onDecide={decide} />}

      {step.decisions.length > 0 && (
        <section className="card">
          <h2>Approval history</h2>
          <ul className="timeline">
            {step.decisions.map((d, i) => (
              <li key={i}><Chip value={d.decision} /> <strong>{d.user.name}</strong>
                <span className="muted small">round {d.round}, {fmt(d.decided_at)}</span>{d.comment && <span>{d.comment}</span>}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
