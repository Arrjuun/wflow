import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Navigate, Route, Routes } from "react-router-dom";
import { fetchMe } from "./slices/authSlice";
import Layout from "./components/Layout";
import { RequireAuth, RequireAdmin } from "./components/Guards";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ChangePassword from "./pages/ChangePassword";
import MyWork from "./pages/MyWork";
import Projects from "./pages/Projects";
import ProjectCreate from "./pages/ProjectCreate";
import ProjectShell from "./pages/ProjectShell";
import ProjectDashboard from "./pages/ProjectDashboard";
import PhasePage from "./pages/PhasePage";
import GateReview from "./pages/GateReview";
import Workflows from "./pages/Workflows";
import WorkflowBuilder from "./pages/WorkflowBuilder";
import AdminUsers from "./pages/AdminUsers";

export default function App() {
  const dispatch = useDispatch();
  const ready = useSelector((s) => s.auth.ready);
  useEffect(() => { dispatch(fetchMe()); }, [dispatch]);
  if (!ready) return <div className="auth muted">Loading…</div>;

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<RequireAuth />}>
        <Route path="/change-password" element={<ChangePassword />} />
        <Route element={<Layout />}>
          <Route index element={<MyWork />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/new" element={<ProjectCreate />} />
          <Route path="projects/:id" element={<ProjectShell />}>
            <Route index element={<ProjectDashboard />} />
            <Route path="phases/:key" element={<PhasePage />} />
            <Route path="phases/:key/gate" element={<GateReview />} />
          </Route>
          <Route path="workflows" element={<Workflows />} />
          <Route path="workflows/:id" element={<WorkflowBuilder />} />
          <Route element={<RequireAdmin />}>
            <Route path="users" element={<AdminUsers />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
