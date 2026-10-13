import { useDispatch, useSelector } from "react-redux";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../slices/authSlice";

export default function Layout() {
  const user = useSelector((s) => s.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const signOut = async () => { await dispatch(logout()); navigate("/login"); };

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">CAF</span>
        <nav aria-label="Main">
          <NavLink to="/" end>My work</NavLink>
          <NavLink to="/projects">Projects</NavLink>
          <NavLink to="/workflows">Workflows</NavLink>
          {user.role === "admin" && <NavLink to="/users">Users</NavLink>}
        </nav>
        <span className="who">
          Welcome, {user.name} | <NavLink to="/change-password">Password</NavLink> | <button className="linkish" onClick={signOut}>Logout</button>
        </span>
      </header>
      <Outlet />
    </div>
  );
}
