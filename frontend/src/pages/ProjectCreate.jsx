import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { fetchWorkflows } from "../slices/workflowsSlice";
import { fetchDirectory } from "../slices/usersSlice";
import { createProject, clearProjectError } from "../slices/projectsSlice";
import TeamPicker from "../components/TeamPicker";
import ProjectDetailsEditor from "../components/ProjectDetailsEditor";
import { Errors, Page } from "../components/Ui";

export default function ProjectCreate() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const workflows = useSelector((s) => s.workflows.list);
  const { error, errors, busy } = useSelector((s) => s.projects);
  const [workflowId, setWorkflowId] = useState("");
  const [details, setDetails] = useState({ name: "", detail_fields: [], detail_values: {} });
  const [members, setMembers] = useState([]);

  useEffect(() => { dispatch(clearProjectError()); dispatch(fetchWorkflows("approved")); dispatch(fetchDirectory()); }, [dispatch]);

  const submit = async (e) => {
    e.preventDefault();
    const res = await dispatch(createProject({ ...details, workflow_id: Number(workflowId), members }));
    if (createProject.fulfilled.match(res)) navigate(`/projects/${res.payload.id}`);
  };

  return (
    <Page>
      <div className="page-head"><div><h1>New project</h1><p className="muted">Pick a workflow, define the project's details and choose the team. You can change details and team later.</p></div></div>
      <form onSubmit={submit}>
        <Errors error={error} errors={errors} />
        <section className="card">
          <h2>Workflow</h2>
          <div className="field"><label htmlFor="wf">Workflow to follow</label>
            <select id="wf" required value={workflowId} onChange={(e) => setWorkflowId(e.target.value)}>
              <option value="">Select a workflow…</option>
              {workflows.map((w) => <option key={w.id} value={w.id}>{w.title} (v{w.version})</option>)}
            </select></div>
        </section>
        <section className="card">
          <h2>Project details</h2>
          <ProjectDetailsEditor value={details} onChange={setDetails} />
        </section>
        <section className="card">
          <h2>Team</h2>
          <p className="muted small">Hold Ctrl (or Cmd) to pick several people. At least one author is required.</p>
          <TeamPicker members={members} onChange={setMembers} />
        </section>
        <button className="btn" disabled={busy}>{busy ? "Creating…" : "Create project"}</button>
      </form>
    </Page>
  );
}
