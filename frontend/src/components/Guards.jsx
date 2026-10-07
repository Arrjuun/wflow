import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export function RequireAuth() {
  const user = useSelector((s) => s.auth.user);
  const { pathname } = useLocation();
  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password && pathname !== "/change-password") return <Navigate to="/change-password" replace />;
  return <Outlet />;
}

export function RequireAdmin() {
  const user = useSelector((s) => s.auth.user);
  return user?.role === "admin" ? <Outlet /> : <Navigate to="/" replace />;
}
