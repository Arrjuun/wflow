import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { fetchActions } from "../slices/phasesSlice";
import { Empty, Page, ROLE_LABEL } from "../components/Ui";

export default function MyWork() {
  const dispatch = useDispatch();
  const actions = useSelector((s) => s.phases.actions);
  useEffect(() => { dispatch(fetchActions()); }, [dispatch]);
  return (
    <Page>
      <div className="page-head"><div><h1>My work</h1><p className="muted">Steps to fill in, steps to approve and phase sign-offs waiting for you.</p></div></div>
      <div className="card flat">
        {!actions.length ? <Empty>Nothing is waiting for you right now.</Empty> : (
          <table>
            <thead><tr><th>Project</th><th>Action</th><th>As</th><th /></tr></thead>
            <tbody>
              {actions.map((a) => (
                <tr key={`${a.project_id}-${a.role}-${a.step_instance_id}`}>
                  <td><Link to={`/projects/${a.project_id}`}>{a.project_name}</Link></td>
                  <td>{a.action}</td>
                  <td>{ROLE_LABEL[a.role]}</td>
                  <td><Link className="btn-link" to={a.kind === "signoff" ? `/projects/${a.project_id}/phases/${a.phase_key}/gate` : `/projects/${a.project_id}/phases/${a.phase_key}?step=${a.step_instance_id}`}>Open</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Page>
  );
}
