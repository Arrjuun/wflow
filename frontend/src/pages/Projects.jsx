import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { fetchProjects } from "../slices/projectsSlice";
import { Chip, Empty, Errors, fmt } from "../components/Ui";

export default function Projects() {
  const dispatch = useDispatch();
  const { list, loading, error } = useSelector((s) => s.projects);
  const [archived, setArchived] = useState(false);
  useEffect(() => { dispatch(fetchProjects(archived)); }, [dispatch, archived]);

  return (
    <>
      <div className="page-head">
        <div><h1>Projects</h1><p className="muted">Runs of approved workflows.</p></div>
        <div className="actions">
          <button className="btn secondary" onClick={() => setArchived(!archived)}>{archived ? "Show active" : "Show archived"}</button>
          <Link to="/projects/new" className="btn" style={{ textDecoration: "none", padding: "8px 14px", background: "var(--accent)", color: "#fff", borderRadius: 6, fontWeight: 600 }}>New project</Link>
        </div>
      </div>
      <Errors error={error} />
      <div className="card flat">
        {!list.length ? <Empty>{loading ? "Loading…" : archived ? "No archived projects." : "No projects yet. Start one from an approved workflow."}</Empty> : (
          <table>
            <thead><tr><th>Name</th><th>Workflow</th><th>Status</th><th>Open steps</th><th>Created</th></tr></thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/projects/${p.id}`}>{p.name}</Link></td>
                  <td>{p.workflow_title}</td>
                  <td><Chip value={p.status} /></td>
                  <td>{p.open_steps.join(", ") || "—"}</td>
                  <td className="muted small">{fmt(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
