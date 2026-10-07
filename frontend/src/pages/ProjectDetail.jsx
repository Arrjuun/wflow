import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";
import { archiveProject, fetchProject, unarchiveProject } from "../slices/projectsSlice";
import { Chip, Errors, fmt } from "../components/Ui";

export default function ProjectDetail() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const { current: p, error, busy } = useSelector((s) => s.projects);
  const user = useSelector((s) => s.auth.user);
  useEffect(() => { dispatch(fetchProject(id)); }, [dispatch, id]);
  if (!p || String(p.id) !== id) return <Errors error={error} />;
  const canManage = user.role === "admin" || p.created_by.id === user.id;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{p.name}</h1>
          <p className="muted">{p.workflow_title} · started by {p.created_by.name} · <Chip value={p.status} /></p>
        </div>
        <div className="actions">
          {canManage && p.status === "completed" && <button className="btn" disabled={busy} onClick={() => dispatch(archiveProject(p.id))}>Archive project</button>}
          {canManage && p.status === "archived" && <button className="btn secondary" disabled={busy} onClick={() => dispatch(unarchiveProject(p.id))}>Restore from archive</button>}
        </div>
      </div>
      <Errors error={error} />
      <div className="card">
        <h2>Path taken</h2>
        <ul className="timeline">
          {p.instances.map((i) => (
            <li key={i.id}>
              <Chip value={i.status} />
              <Link to={`/steps/${i.id}`}>{i.step_key}. {i.step_name}</Link>
              <span className="muted small">{i.assignee.name}{i.round > 1 ? ` · round ${i.round}` : ""}{i.completed_at ? ` · done ${fmt(i.completed_at)}` : ""}</span>
            </li>
          ))}
        </ul>
        {p.status === "active" && <p className="muted small">The next step is created when the current one is approved, based on the values entered.</p>}
        {p.status === "completed" && <p className="small">All steps are finished. Archive the project to remove it from active lists.</p>}
      </div>
    </>
  );
}
