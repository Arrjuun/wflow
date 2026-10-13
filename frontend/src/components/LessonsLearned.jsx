import { useState } from "react";
import { useDispatch } from "react-redux";
import { addLesson, deleteLesson } from "../slices/projectsSlice";
import { Empty, fmt } from "./Ui";

// Lessons learned for the project. Added by the project creator (or an admin); not part of any approval.
export default function LessonsLearned({ p }) {
  const dispatch = useDispatch();
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ title: "", body: "" });
  const editable = p.can_manage;

  const save = async (e) => {
    e.preventDefault();
    const res = await dispatch(addLesson({ id: p.id, ...form }));
    if (addLesson.fulfilled.match(res)) { setForm({ title: "", body: "" }); setAdding(false); }
  };

  return (
    <section className="card">
      <div className="card-head"><h2>Lessons learned</h2>
        {editable && !adding && <button className="btn secondary small" onClick={() => setAdding(true)}>Add lesson</button>}</div>
      {!p.lessons.length && !adding && (
        <Empty>No lessons recorded yet.{editable ? " Add them at any time, including after the project is completed." : ""}</Empty>
      )}
      <ul className="refs">
        {p.lessons.map((l) => (
          <li key={l.id}>
            <div>
              <strong>{l.title}</strong>
              {l.body && <div style={{ whiteSpace: "pre-wrap" }}>{l.body}</div>}
              <div className="muted small">{l.created_by?.name}, {fmt(l.created_at)}</div>
            </div>
            {editable && <button className="btn danger small" onClick={() => dispatch(deleteLesson({ id: p.id, lessonId: l.id }))}>Remove</button>}
          </li>
        ))}
      </ul>
      {adding && (
        <form onSubmit={save} className="ref-form">
          <div className="field"><label htmlFor="lt">Title</label>
            <input id="lt" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
          <div className="field"><label htmlFor="lb">What did we learn?</label>
            <textarea id="lb" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></div>
          <div className="actions">
            <button className="btn">Save lesson</button>
            <button type="button" className="btn secondary" onClick={() => { setAdding(false); setForm({ title: "", body: "" }); }}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  );
}
