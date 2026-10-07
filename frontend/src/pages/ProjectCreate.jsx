import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { fetchWorkflows, fetchWorkflow } from "../slices/workflowsSlice";
import { fetchDirectory } from "../slices/usersSlice";
import { createProject, clearProjectError } from "../slices/projectsSlice";
import { Errors } from "../components/Ui";

export default function ProjectCreate() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { list, current } = useSelector((s) => s.workflows);
  const directory = useSelector((s) => s.users.directory);
  const { error, busy } = useSelector((s) => s.projects);
  const [workflowId, setWorkflowId] = useState("");
  const [name, setName] = useState("");
  const [assign, setAssign] = useState({});
  const [approvers, setApprovers] = useState({});

  useEffect(() => {
    dispatch(clearProjectError());
    dispatch(fetchWorkflows("approved"));
    dispatch(fetchDirectory());
  }, [dispatch]);
  useEffect(() => {
    if (workflowId) { dispatch(fetchWorkflow(workflowId)); setAssign({}); setApprovers({}); }
  }, [dispatch, workflowId]);

  const wf = current && String(current.id) === String(workflowId) ? current : null;

  const submit = async (e) => {
    e.preventDefault();
    const assignments = Object.fromEntries(Object.entries(assign).filter(([, v]) => v).map(([k, v]) => [k, Number(v)]));
    const res = await dispatch(createProject({ workflow_id: Number(workflowId), name, assignments, approvers }));
    if (createProject.fulfilled.match(res)) navigate(`/projects/${res.payload.id}`);
  };

  return (
    <>
      <div className="page-head"><div><h1>New project</h1><p className="muted">Pick a workflow, then say who does and who approves each step.</p></div></div>
      <form onSubmit={submit}>
        <Errors error={error} />
        <div className="card">
          <div className="row">
            <div className="field"><label htmlFor="wf">Workflow</label>
              <select id="wf" required value={workflowId} onChange={(e) => setWorkflowId(e.target.value)}>
                <option value="">Select a workflow…</option>
                {list.map((w) => <option key={w.id} value={w.id}>{w.title} (v{w.version})</option>)}
              </select></div>
            <div className="field"><label htmlFor="pname">Project name</label>
              <input id="pname" required value={name} onChange={(e) => setName(e.target.value)} /></div>
          </div>
        </div>
        {wf && (
          <div className="card">
            <h2>Steps</h2>
            <p className="muted small">Steps on a branch you never take are skipped automatically, but each still needs an assignee.</p>
            {wf.steps.map((s) => (
              <div className="step-card" key={s.key}>
                <h3>{s.key}. {s.name} {s.is_terminal && <span className="chip">end</span>}</h3>
                <div className="row">
                  <div><label htmlFor={`a-${s.key}`}>Assigned to</label>
                    <select id={`a-${s.key}`} required value={assign[s.key] || ""} onChange={(e) => setAssign({ ...assign, [s.key]: e.target.value })}>
                      <option value="">Select a user…</option>
                      {directory.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                    </select></div>
                  <div><label htmlFor={`p-${s.key}`}>Approvers (optional, {s.approval_policy === "all" ? "all must approve" : "any one approves"})</label>
                    <select id={`p-${s.key}`} multiple value={(approvers[s.key] || []).map(String)}
                      onChange={(e) => setApprovers({ ...approvers, [s.key]: [...e.target.selectedOptions].map((o) => Number(o.value)) })}>
                      {directory.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                    </select></div>
                </div>
              </div>
            ))}
          </div>
        )}
        <button className="btn" disabled={busy || !wf}>{busy ? "Creating…" : "Create project"}</button>
      </form>
    </>
  );
}
