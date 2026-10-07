import { createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { thunk, errorOf } from "../thunk";

export const fetchTasks = thunk("tasks/mine", () => api.get("/tasks/mine"));
export const fetchApprovals = thunk("tasks/approvals", () => api.get("/approvals/mine"));
export const fetchInstance = thunk("tasks/instance", (id) => api.get(`/step-instances/${id}`));
export const saveValues = thunk("tasks/save", ({ id, values }) => api.put(`/step-instances/${id}/values`, { values }));
export const submitInstance = thunk("tasks/submit", ({ id, values }) => api.post(`/step-instances/${id}/submit`, { values }));
export const decideInstance = thunk("tasks/decide", ({ id, decision, comment }) =>
  api.post(`/step-instances/${id}/decision`, { decision, comment }));

const slice = createSlice({
  name: "tasks",
  initialState: { tasks: [], approvals: [], instance: null, loading: false, busy: false, error: null, errors: null, saved: false },
  reducers: { clearInstance: (s) => { s.instance = null; s.error = null; s.errors = null; s.saved = false; } },
  extraReducers: (b) => {
    b.addCase(fetchTasks.fulfilled, (s, a) => { s.tasks = a.payload; })
      .addCase(fetchApprovals.fulfilled, (s, a) => { s.approvals = a.payload; })
      .addCase(fetchInstance.pending, (s) => { s.loading = true; })
      .addCase(fetchInstance.fulfilled, (s, a) => { s.loading = false; s.instance = a.payload; })
      .addCase(fetchInstance.rejected, (s, a) => { s.loading = false; s.error = errorOf(a); });
    for (const t of [saveValues, submitInstance, decideInstance]) {
      b.addCase(t.pending, (s) => { s.busy = true; s.error = null; s.errors = null; s.saved = false; })
        .addCase(t.fulfilled, (s, a) => { s.busy = false; s.instance = a.payload; s.saved = true; })
        .addCase(t.rejected, (s, a) => { s.busy = false; s.error = errorOf(a); s.errors = a.payload?.errors || null; });
    }
  },
});
export const { clearInstance } = slice.actions;
export default slice.reducer;
