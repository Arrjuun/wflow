import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { fetchApprovals, fetchTasks } from "../slices/tasksSlice";
import { Empty, fmt } from "../components/Ui";

function Table({ rows, action, empty }) {
  if (!rows.length) return <div className="card"><Empty>{empty}</Empty></div>;
  return (
    <div className="card flat">
      <table>
        <thead><tr><th>Project</th><th>Step</th><th>{action === "Review" ? "Submitted" : "Round"}</th><th /></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td><Link to={`/projects/${r.project_id}`}>{r.project_name}</Link></td>
              <td>{r.step_key}. {r.step_name}</td>
              <td>{action === "Review" ? fmt(r.submitted_at) : r.round > 1 ? `Rework (round ${r.round})` : "New"}</td>
              <td><Link className="btn small" to={`/steps/${r.id}`} style={{ textDecoration: "none", display: "inline-block", padding: "4px 10px", background: "var(--accent)", color: "#fff", borderRadius: 6 }}>{action}</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MyWork() {
  const dispatch = useDispatch();
  const { tasks, approvals } = useSelector((s) => s.tasks);
  useEffect(() => { dispatch(fetchTasks()); dispatch(fetchApprovals()); }, [dispatch]);
  return (
    <>
      <div className="page-head"><div><h1>My work</h1><p className="muted">Steps assigned to you and steps waiting for your approval.</p></div></div>
      <h2>To fill in</h2>
      <Table rows={tasks} action="Open" empty="Nothing assigned to you right now." />
      <h2>To approve</h2>
      <Table rows={approvals} action="Review" empty="Nothing waiting for your approval." />
    </>
  );
}
