import { useState } from "react";
import { useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import { signOff } from "../slices/phasesSlice";
import { fetchProject } from "../slices/projectsSlice";
import StepForm from "../components/StepForm";
import { Alert, Chip, Errors, fmt } from "../components/Ui";
import { usePhaseInstance } from "./PhasePage";

export default function GateReview() {
  const dispatch = useDispatch();
  const { id, key, phase, inst, error, errors, busy, notice } = usePhaseInstance();
  const [comment, setComment] = useState("");

  if (!phase) return <Errors error="This phase does not exist in the project's workflow." />;
  const title = `${phase.name} gate review`;
  if (!phase.instance_id) return <><h1>{title}</h1><div className="card"><p className="muted">This phase has not started yet.</p></div></>;
  if (!inst) return <Errors error={error} />;

  const approved = inst.steps.filter((s) => s.status === "approved").length;
  const decide = async (decision) => {
    const res = await dispatch(signOff({ id: inst.id, decision, comment }));
    if (signOff.fulfilled.match(res)) { setComment(""); dispatch(fetchProject(id)); }
  };

  return (
    <>
      <div className="page-head"><h1>{title}</h1><Chip value={inst.status} /></div>
      <Errors error={error} errors={errors} />
      <Alert tone="ok">{notice}</Alert>
      {inst.status === "in_progress" && (
        <Alert tone="warn">{approved} of {inst.steps.length} steps approved. Sign-off opens when every step is approved.</Alert>
      )}

      <section className="card">
        <h2>Steps</h2>
        <div className="scroll-x"><table>
          <thead><tr><th>Step</th><th>Status</th><th>Approved by</th></tr></thead>
          <tbody>
            {inst.steps.map((s) => (
              <tr key={s.id}>
                <td><Link to={`/projects/${id}/phases/${key}?step=${s.id}`}>{s.name}</Link></td>
                <td><Chip value={s.status} /></td>
                <td>{s.decisions.filter((d) => d.round === s.round && d.decision === "approved").map((d) => d.user.name).join(", ") || <span className="muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        <p className="muted small">
          Authorizers: {inst.authorizers.map((u) => u.name).join(", ") || "none, so the phase completes when every step is approved"}.
        </p>
      </section>

      {inst.can_sign_off && (
        <section className="card decision">
          <h2>Your sign-off</h2>
          <div className="field"><label htmlFor="cm">Comment (required when sending back)</label>
            <textarea id="cm" value={comment} onChange={(e) => setComment(e.target.value)} /></div>
          <div className="actions">
            <button className="btn" disabled={busy} onClick={() => decide("approved")}>Sign off phase</button>
            <button className="btn danger" disabled={busy} onClick={() => decide("rejected")}>Send whole phase back to team</button>
          </div>
        </section>
      )}

      <section className="card">
        <h2>What was submitted</h2>
        {inst.steps.map((s) => (
          <div key={s.id} className="review-step">
            <h3>{s.name}</h3>
            <StepForm fields={s.fields} values={inst.values} onChange={() => {}} disabled />
          </div>
        ))}
      </section>

      {inst.gate_decisions.length > 0 && (
        <section className="card">
          <h2>Sign-off history</h2>
          <ul className="timeline">
            {inst.gate_decisions.map((d, i) => (
              <li key={i}><Chip value={d.decision} /> <strong>{d.user.name}</strong>
                <span className="muted small">round {d.round}, {fmt(d.decided_at)}</span>{d.comment && <span>{d.comment}</span>}</li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
