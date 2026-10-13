import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { approveUser, fetchUsers, patchUser, resetPassword } from "../slices/usersSlice";
import { Alert, Chip, Empty, Errors, Page } from "../components/Ui";

export default function AdminUsers() {
  const dispatch = useDispatch();
  const { list, tempPasswords, error, loading } = useSelector((s) => s.users);
  const me = useSelector((s) => s.auth.user);
  const [tab, setTab] = useState("pending");
  useEffect(() => { dispatch(fetchUsers()); }, [dispatch]);
  const rows = tab === "pending" ? list.filter((u) => u.status === "pending") : list;
  const pendingCount = list.filter((u) => u.status === "pending").length;

  return (
    <Page>
      <div className="page-head"><div><h1>Users</h1><p className="muted">Approve new accounts, change roles and reset passwords.</p></div>
        <div className="actions">
          <button className={`btn ${tab === "pending" ? "" : "secondary"}`} onClick={() => setTab("pending")}>Waiting for approval ({pendingCount})</button>
          <button className={`btn ${tab === "all" ? "" : "secondary"}`} onClick={() => setTab("all")}>All users</button>
        </div>
      </div>
      <Errors error={error} />
      <div className="card flat">
        {!rows.length ? <Empty>{loading ? "Loading…" : tab === "pending" ? "No accounts are waiting for approval." : "No users."}</Empty> : (
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Role</th><th /></tr></thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id}>
                  <td>{u.name}</td><td>{u.email}</td><td><Chip value={u.status} /></td>
                  <td>
                    <select aria-label={`Role for ${u.name}`} style={{ width: 110 }} value={u.role} disabled={u.id === me.id || u.status === "pending"}
                      onChange={(e) => dispatch(patchUser({ id: u.id, role: e.target.value }))}>
                      <option value="user">user</option><option value="admin">admin</option>
                    </select>
                  </td>
                  <td>
                    <div className="actions">
                      {u.status === "pending" && <button className="btn small" onClick={() => dispatch(approveUser(u.id))}>Approve</button>}
                      {u.status === "active" && u.id !== me.id && <>
                        <button className="btn secondary small" onClick={() => dispatch(resetPassword(u.id))}>Reset password</button>
                        <button className="btn danger small" onClick={() => dispatch(patchUser({ id: u.id, status: "disabled" }))}>Disable</button>
                      </>}
                      {u.status === "disabled" && <button className="btn secondary small" onClick={() => dispatch(patchUser({ id: u.id, status: "active" }))}>Enable</button>}
                    </div>
                    {tempPasswords[u.id] && <Alert tone="warn">Temporary password: <strong>{tempPasswords[u.id]}</strong>. Share it securely; they must change it at next sign-in.</Alert>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Page>
  );
}
