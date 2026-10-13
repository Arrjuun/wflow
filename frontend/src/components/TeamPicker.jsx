import { useSelector } from "react-redux";
import { ROLE_LABEL } from "./Ui";

const HELP = {
  author: "Project team: fills in and submits steps",
  approver: "Approves every submitted step (any one approves)",
  authorizer: "Signs off each phase gate once its steps are approved (any one)",
};

// members: [{user_id, role}]
export default function TeamPicker({ members, onChange }) {
  const directory = useSelector((s) => s.users.directory);
  return Object.keys(ROLE_LABEL).map((role) => {
    const selected = members.filter((m) => m.role === role).map((m) => String(m.user_id));
    const set = (ids) => onChange([...members.filter((m) => m.role !== role), ...ids.map((id) => ({ user_id: Number(id), role }))]);
    return (
      <div className="field" key={role}>
        <label htmlFor={`r-${role}`}>{ROLE_LABEL[role]}s <span className="muted small">({HELP[role]})</span></label>
        <select id={`r-${role}`} multiple size={Math.min(5, Math.max(directory.length, 2))} value={selected}
          onChange={(e) => set([...e.target.selectedOptions].map((o) => o.value))}>
          {directory.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.email})</option>)}
        </select>
      </div>
    );
  });
}
