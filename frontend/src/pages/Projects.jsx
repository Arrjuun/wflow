import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { fetchProjects } from "../slices/projectsSlice";
import { Chip, Empty, Errors, Page } from "../components/Ui";

export default function Projects() {
  const dispatch = useDispatch();
  const { list, loading, error } = useSelector((s) => s.projects);
  const [archived, setArchived] = useState(false);
  useEffect(() => { dispatch(fetchProjects(archived)); }, [dispatch, archived]);

  return (
    <Page>
      <div className="page-head">
        <div><h1>Projects</h1><p className="muted">Each project follows an approved workflow, phase by phase.</p></div>
        <div className="actions">
          <button className="btn secondary" onClick={() => setArchived(!archived)}>{archived ? "Show active" : "Show archived"}</button>
          <Link to="/projects/new" className="btn-link primary">New project</Link>
        </div>
      </div>
      <Errors error={error} />
      <div className="card flat">
        {!list.length ? <Empty>{loading ? "Loading…" : archived ? "No archived projects." : "No projects yet. Start one from an approved workflow."}</Empty> : (
          <table>
            <thead><tr><th>Name</th><th>Workflow</th><th>Current stage</th><th>Progress</th><th>Status</th></tr></thead>
            <tbody>
              {list.map((p) => (
                <tr key={p.id}>
                  <td><Link to={`/projects/${p.id}`}>{p.name}</Link></td>
                  <td>{p.workflow_title}</td>
                  <td>{p.stage}</td>
                  <td style={{ minWidth: 120 }}><div className="progress thin"><div style={{ width: `${p.progress}%` }} /></div><span className="small muted">{p.progress}%</span></td>
                  <td><Chip value={p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Page>
  );
}
