import { useState } from "react";
import { useDispatch } from "react-redux";
import { api } from "../api";
import { addReference, deleteReference } from "../slices/projectsSlice";
import { Empty } from "./Ui";

// Reference material for the project. Managed by the project creator; not part of any approval.
export default function References({ p }) {
  const dispatch = useDispatch();
  const blank = { title: "", url: "", note: "", file: null };
  const [form, setForm] = useState(blank);
  const [adding, setAdding] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const editable = p.can_manage && p.status !== "archived";

  const pickFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadError("");
    try { setForm((f) => ({ ...f, file: { file_id: null, name: file.name }, uploading: true })); 
      const up = await api.upload(file);
      setForm((f) => ({ ...f, file: up, uploading: false, title: f.title || up.name }));
    } catch (err) { setUploadError(err.message); setForm((f) => ({ ...f, file: null, uploading: false })); }
  };
  const save = async (e) => {
    e.preventDefault();
    const res = await dispatch(addReference({ id: p.id, title: form.title, url: form.url, note: form.note, file_id: form.file?.file_id || null }));
    if (addReference.fulfilled.match(res)) { setForm(blank); setAdding(false); }
  };

  return (
    <section className="card">
      <div className="card-head"><h2>References</h2>
        {editable && !adding && <button className="btn secondary small" onClick={() => setAdding(true)}>Add reference</button>}</div>
      {!p.references.length && !adding && <Empty>No references yet.{editable ? " Add standards, reports or links the team should use." : ""}</Empty>}
      <ul className="refs">
        {p.references.map((r) => (
          <li key={r.id}>
            <div>
              <strong>{r.title}</strong>
              {r.url && <> · <a href={r.url} target="_blank" rel="noreferrer">Open link</a></>}
              {r.file && <> · <a href={`/api/v1/files/${r.file.file_id}`}>{r.file.name}</a></>}
              {r.note && <div className="muted small">{r.note}</div>}
            </div>
            {editable && <button className="btn danger small" onClick={() => dispatch(deleteReference({ id: p.id, refId: r.id }))}>Remove</button>}
          </li>
        ))}
      </ul>
      {adding && (
        <form onSubmit={save} className="ref-form">
          <div className="form-grid">
            <div className="field half"><label htmlFor="rt">Title</label><input id="rt" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="field half"><label htmlFor="ru">Link (optional)</label><input id="ru" type="url" placeholder="https://" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /></div>
            <div className="field half"><label htmlFor="rf">File (optional)</label><input id="rf" type="file" onChange={pickFile} />
              {form.uploading && <div className="hint">Uploading…</div>}{uploadError && <div className="hint bad">{uploadError}</div>}</div>
            <div className="field half"><label htmlFor="rn2">Note (optional)</label><input id="rn2" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></div>
          </div>
          <div className="actions">
            <button className="btn" disabled={form.uploading || (!form.url && !form.file?.file_id)}>Save reference</button>
            <button type="button" className="btn secondary" onClick={() => { setAdding(false); setForm(blank); }}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  );
}
