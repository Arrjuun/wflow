import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, Navigate } from "react-router-dom";
import { login, clearMessages } from "../slices/authSlice";
import { Errors } from "../components/Ui";

export default function Login() {
  const dispatch = useDispatch();
  const { user, error, busy } = useSelector((s) => s.auth);
  const [form, setForm] = useState({ email: "", password: "" });
  if (user) return <Navigate to="/" replace />;

  const submit = (e) => {
    e.preventDefault();
    dispatch(login(form));
  };
  return (
    <div className="auth">
      <form className="card" onSubmit={submit}>
        <h1>Sign in</h1>
        <p className="muted">CAF</p>
        <Errors error={error} />
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" required value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        <button className="btn" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="small">No account? <Link to="/register" onClick={() => dispatch(clearMessages())}>Request one</Link></p>
      </form>
    </div>
  );
}
