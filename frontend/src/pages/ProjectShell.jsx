import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { fetchProject } from "../slices/projectsSlice";
import { Errors } from "../components/Ui";

const MARK = { approved: "✓", in_progress: "●", in_review: "●", awaiting_signoff: "●" };

// Left-hand navigation for one project: dashboard, each phase, and each phase's gate review.
export default function ProjectShell() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const { current: p, error } = useSelector((s) => s.projects);
  useEffect(() => { dispatch(fetchProject(id)); }, [dispatch, id]);
  if (!p || String(p.id) !== id) return <main className="page"><Errors error={error} /></main>;

  const gateState = (ph) => (ph.status === "approved" ? "approved" : ["in_review", "awaiting_signoff"].includes(ph.status) ? "in_progress" : "not_started");

  return (
    <div className="project">
      <nav className="phase-nav" aria-label="Project">
        <NavLink to={`/projects/${p.id}`} end>Dashboard</NavLink>
        {p.phases.map((ph) => (
          <div key={ph.key} className={ph.status === "not_started" ? "unreached" : ""}>
            <NavLink to={`/projects/${p.id}/phases/${ph.key}`}>
              <span className={`mark ${ph.status}`}>{MARK[ph.status] || ""}</span>{ph.name}
            </NavLink>
            {ph.requires_gate && (
              <NavLink to={`/projects/${p.id}/phases/${ph.key}/gate`} className="gate">
                <span className={`mark ${gateState(ph)}`}>{MARK[gateState(ph)] || ""}</span>{ph.name.split(":")[0]} Gate Review
              </NavLink>
            )}
          </div>
        ))}
      </nav>
      <main className="page"><Outlet /></main>
    </div>
  );
}
