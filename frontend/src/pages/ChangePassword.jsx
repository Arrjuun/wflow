import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../slices/authSlice";
import { Alert, Errors } from "../components/Ui";

export default function ChangePassword() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user, error, busy } = useSelector((s) => s.auth);
  const [form, setForm] = useState({ current_password: "", new_password: "" });
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const res = await dispatch(changePassword(form));
    if (changePassword.fulfilled.match(res)) {
      setDone(true);
      setForm({ current_password: "", new_password: "" });
      navigate("/");
    }
  };
  return (
    <div className={user.must_change_password ? "auth" : "page"}>
      <form className="card" style={{ maxWidth: 420 }} onSubmit={submit}>
        <h1>Change password</h1>
        {user.must_change_password && <Alert tone="warn">An admin reset your password. Choose a new one to continue.</Alert>}
        <Errors error={error} />
        <Alert tone="ok">{done && "Password updated"}</Alert>
        <div className="field"><label htmlFor="cur">Current password</label>
          <input id="cur" type="password" required value={form.current_password}
            onChange={(e) => setForm({ ...form, current_password: e.target.value })} /></div>
        <div className="field"><label htmlFor="new">New password (8+ characters)</label>
          <input id="new" type="password" minLength={8} required value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })} /></div>
        <button className="btn" disabled={busy}>Save password</button>
      </form>
    </div>
  );
}
