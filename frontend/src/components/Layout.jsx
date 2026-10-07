import { useDispatch, useSelector } from "react-redux";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../slices/authSlice";

export default function Layout() {
  const user = useSelector((s) => s.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const link = ({ isActive }) => (isActive ? "active" : undefined);

  const signOut = async () => {
    await dispatch(logout());
    navigate("/login");
  };

  return (
    <div className="shell">
      <nav className="side" aria-label="Main">
        <div className="brand">Workflow Desk</div>
        <NavLink to="/" end className={link}>My work</NavLink>
        <NavLink to="/projects" className={link}>Projects</NavLink>
        <NavLink to="/workflows" className={link}>Workflows</NavLink>
        {user.role === "admin" && <NavLink to="/users" className={link}>Users</NavLink>}
        <div className="spacer" />
        <div className="who">{user.name}{user.role === "admin" ? " (admin)" : ""}</div>
        <NavLink to="/change-password" className={link}>Change password</NavLink>
        <button className="link" onClick={signOut}>Sign out</button>
      </nav>
      <main className="main"><Outlet /></main>
    </div>
  );
}
