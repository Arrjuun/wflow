import { createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { thunk, errorOf } from "../thunk";

export const fetchWorkflows = thunk("workflows/list", (scope = "visible") => api.get(`/workflows?scope=${scope}`));
export const fetchWorkflow = thunk("workflows/get", (id) => api.get(`/workflows/${id}`));
export const fetchFieldTypes = thunk("workflows/fieldTypes", () => api.get("/field-types"));
export const createWorkflow = thunk("workflows/create", (b) => api.post("/workflows", b));
export const saveWorkflow = thunk("workflows/save", ({ id, data }) => api.put(`/workflows/${id}`, data));
export const submitWorkflow = thunk("workflows/submit", (id) => api.post(`/workflows/${id}/submit`));
export const approveWorkflow = thunk("workflows/approve", (id) => api.post(`/workflows/${id}/approve`));
export const rejectWorkflow = thunk("workflows/reject", ({ id, comment }) => api.post(`/workflows/${id}/reject`, { comment }));
export const retireWorkflow = thunk("workflows/retire", (id) => api.post(`/workflows/${id}/retire`));
export const cloneWorkflow = thunk("workflows/clone", (id) => api.post(`/workflows/${id}/clone`));
export const deleteWorkflow = thunk("workflows/delete", async (id) => { await api.del(`/workflows/${id}`); return id; });

const setCurrent = (s, a) => { s.current = a.payload; s.busy = false; s.error = null; s.errors = null; };
const fail = (s, a) => { s.busy = false; s.error = errorOf(a); s.errors = a.payload?.errors || null; };
const start = (s) => { s.busy = true; s.error = null; s.errors = null; };

const slice = createSlice({
  name: "workflows",
  initialState: { list: [], current: null, fieldTypes: [], loading: false, busy: false, error: null, errors: null },
  reducers: { clearCurrent: (s) => { s.current = null; s.error = null; s.errors = null; } },
  extraReducers: (b) => {
    b.addCase(fetchWorkflows.pending, (s) => { s.loading = true; })
      .addCase(fetchWorkflows.fulfilled, (s, a) => { s.loading = false; s.list = a.payload; })
      .addCase(fetchWorkflows.rejected, (s, a) => { s.loading = false; s.error = errorOf(a); })
      .addCase(fetchWorkflow.pending, (s) => { s.loading = true; })
      .addCase(fetchWorkflow.fulfilled, (s, a) => { setCurrent(s, a); s.loading = false; })
      .addCase(fetchWorkflow.rejected, (s, a) => { fail(s, a); s.loading = false; })
      .addCase(fetchFieldTypes.fulfilled, (s, a) => { s.fieldTypes = a.payload; })
      .addCase(deleteWorkflow.fulfilled, (s, a) => { s.list = s.list.filter((w) => w.id !== a.payload); });
    for (const t of [createWorkflow, saveWorkflow, submitWorkflow, approveWorkflow, rejectWorkflow, retireWorkflow, cloneWorkflow]) {
      b.addCase(t.pending, start).addCase(t.fulfilled, setCurrent).addCase(t.rejected, fail);
    }
  },
});
export const { clearCurrent } = slice.actions;
export default slice.reducer;
