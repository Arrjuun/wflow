import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { archiveProject, setMembers, unarchiveProject, updateDetails } from "../slices/projectsSlice";
import { fetchDirectory } from "../slices/usersSlice";
import { Chip, Errors, ROLE_LABEL } from "../components/Ui";
import References from "../components/References";
import LessonsLearned from "../components/LessonsLearned";
import TeamPicker from "../components/TeamPicker";
import ProjectDetailsEditor from "../components/ProjectDetailsEditor";
import { fieldUI } from "../fields/registry";

function Details({ p }) {
  const dispatch = useDispatch();
  const [draft, setDraft] = useState(null);
  const open = () => setDraft({ name: p.name, detail_fields: p.detail_fields, detail_values: p.detail_values });
  const save = async () => {
    const res = await dispatch(updateDetails({ id: p.id, ...draft }));
    if (updateDetails.fulfilled.match(res)) setDraft(null);
  };

  if (draft) return (
    <section className="card">
      <h2>Project details</h2>
      <ProjectDetailsEditor value={draft} onChange={setDraft} />
      <div className="actions" style={{ marginTop: 16 }}>
        <button className="btn" onClick={save}>Save details</button>
        <button className="btn secondary" onClick={() => setDraft(null)}>Cancel</button>
      </div>
    </section>
  );
  const shown = p.detail_fields.filter((f) => f.type !== "heading");
  return (
    <section className="card">
      <div className="card-head"><h2>Project details</h2>{p.can_manage && p.status !== "archived" && <button className="btn secondary small" onClick={open}>Edit details</button>}</div>
      <dl className="kv">
        <dt>Name</dt><dd>{p.name}</dd>
        <dt>Workflow</dt><dd>{p.workflow_title}</dd>
        {shown.map((f) => {
          const v = p.detail_values[f.key];
          const { Viewer } = fieldUI(f.type);
          return [<dt key={`t${f.key}`}>{f.label}</dt>, <dd key={`d${f.key}`}>{v != null && v !== "" ? <Viewer field={f} value={v} /> : <span className="muted">—</span>}</dd>];
        })}
        <dt>Current stage</dt><dd>{p.stage} <Chip value={p.status} /></dd>
      </dl>
      <div className="progress" role="progressbar" aria-valuenow={p.progress} aria-valuemin={0} aria-valuemax={100}>
        <div style={{ width: `${Math.max(p.progress, 4)}%` }}>{p.progress}%</div>
      </div>
    </section>
  );
}

function Team({ p }) {
  const dispatch = useDispatch();
  const [edit, setEdit] = useState(false);
  const [members, setLocal] = useState([]);
  const open = () => { dispatch(fetchDirectory()); setLocal(p.team.map((m) => ({ user_id: m.user.id, role: m.role }))); setEdit(true); };
  const save = async () => {
    const res = await dispatch(setMembers({ id: p.id, members }));
    if (setMembers.fulfilled.match(res)) setEdit(false);
  };
  return (
    <section className="card">
      <div className="card-head"><h2>Team members &amp; roles</h2>
        {p.can_manage && p.status !== "archived" && !edit && <button className="btn secondary small" onClick={open}>Manage team</button>}</div>
      {edit ? (
        <>
          <p className="muted small">Approvers and authorizers can change at any time. Steps awaiting approval are re-checked against the new team.</p>
          <TeamPicker members={members} onChange={setLocal} />
          <div className="actions"><button className="btn" onClick={save}>Save team</button><button className="btn secondary" onClick={() => setEdit(false)}>Cancel</button></div>
        </>
      ) : (
        <div className="scroll-x"><table>
          <thead><tr><th>Name</th><th>Role</th><th>Pending actions</th></tr></thead>
          <tbody>
            {p.team.map((m) => (
              <tr key={`${m.user.id}-${m.role}`}><td>{m.user.name}</td><td>{ROLE_LABEL[m.role]}</td><td>{m.pending.length ? m.pending.join("; ") : <span className="muted">None</span>}</td></tr>
            ))}
          </tbody>
        </table></div>
      )}
    </section>
  );
}

export default function ProjectDashboard() {
  const dispatch = useDispatch();
  const { current: p, error, errors, busy } = useSelector((s) => s.projects);
  useEffect(() => { dispatch(fetchDirectory()); }, [dispatch]);
  return (
    <>
      <div className="page-head">
        <h1>Project dashboard</h1>
        <div className="actions">
          {p.can_manage && p.status === "completed" && <button className="btn" disabled={busy} onClick={() => dispatch(archiveProject(p.id))}>Archive project</button>}
          {p.can_manage && p.status === "archived" && <button className="btn secondary" disabled={busy} onClick={() => dispatch(unarchiveProject(p.id))}>Restore from archive</button>}
        </div>
      </div>
      <Errors error={error} errors={errors} />
      <Details p={p} />
      <Team p={p} />
      <References p={p} />
      <LessonsLearned p={p} />
    </>
  );
}
