import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { createWorkflow, fetchWorkflows } from "../slices/workflowsSlice";
import { Chip, Empty, Errors } from "../components/Ui";

export default function Workflows() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { list, loading, error } = useSelector((s) => s.workflows);
  const user = useSelector((s) => s.auth.user);
  const [title, setTitle] = useState("");
  useEffect(() => { dispatch(fetchWorkflows("visible")); }, [dispatch]);

  const create = async (e) => {
    e.preventDefault();
    const res = await dispatch(createWorkflow({ title }));
    if (createWorkflow.fulfilled.match(res)) navigate(`/workflows/${res.payload.id}`);
  };
  const pendingCount = list.filter((w) => w.status === "pending_approval").length;

  return (
    <>
      <div className="page-head"><div><h1>Workflows</h1>
        <p className="muted">Reusable step-by-step processes. An admin must approve a workflow before projects can use it.</p></div></div>
      <Errors error={error} />
      {user.role === "admin" && pendingCount > 0 && <div className="alert warn">{pendingCount} workflow{pendingCount > 1 ? "s are" : " is"} waiting for your approval.</div>}
      <form className="card actions" onSubmit={create}>
        <input style={{ maxWidth: 360 }} aria-label="New workflow title" placeholder="Title of a new workflow" required value={title} onChange={(e) => setTitle(e.target.value)} />
        <button className="btn">Create workflow</button>
      </form>
      <div className="card flat">
        {!list.length ? <Empty>{loading ? "Loading…" : "No workflows yet."}</Empty> : (
          <table>
            <thead><tr><th>Title</th><th>Version</th><th>Status</th><th>Owner</th><th>Steps</th></tr></thead>
            <tbody>
              {list.map((w) => (
                <tr key={w.id}>
                  <td><Link to={`/workflows/${w.id}`}>{w.title}</Link></td>
                  <td>v{w.version}</td><td><Chip value={w.status} /></td>
                  <td>{w.owner?.name}</td><td>{w.step_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
