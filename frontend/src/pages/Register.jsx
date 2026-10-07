import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { register, clearMessages } from "../slices/authSlice";
import { Alert, Errors } from "../components/Ui";

export default function Register() {
  const dispatch = useDispatch();
  const { error, notice, busy } = useSelector((s) => s.auth);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="auth">
      <form className="card" onSubmit={(e) => { e.preventDefault(); dispatch(register(form)); }}>
        <h1>Request an account</h1>
        <p className="muted">An admin approves new accounts before you can sign in.</p>
        <Errors error={error} />
        <Alert tone="ok">{notice}</Alert>
        <div className="field"><label htmlFor="name">Name</label>
          <input id="name" required value={form.name} onChange={set("name")} /></div>
        <div className="field"><label htmlFor="email">Email</label>
          <input id="email" type="email" required value={form.email} onChange={set("email")} /></div>
        <div className="field"><label htmlFor="pw">Password (8+ characters)</label>
          <input id="pw" type="password" minLength={8} required autoComplete="new-password" value={form.password} onChange={set("password")} /></div>
        <button className="btn" disabled={busy}>Request account</button>
        <p className="small"><Link to="/login" onClick={() => dispatch(clearMessages())}>Back to sign in</Link></p>
      </form>
    </div>
  );
}
