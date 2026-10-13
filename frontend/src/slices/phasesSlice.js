import { createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { thunk, errorOf } from "../thunk";

export const fetchActions = thunk("phases/actions", () => api.get("/me/actions"));
export const fetchInstance = thunk("phases/get", (id) => api.get(`/phase-instances/${id}`));
export const saveValues = thunk("phases/save", ({ id, values }) => api.put(`/phase-instances/${id}/values`, { values }));
export const submitStep = thunk("phases/submitStep", ({ stepId, values }) => api.post(`/step-instances/${stepId}/submit`, { values }));
export const decideStep = thunk("phases/decideStep", ({ stepId, decision, comment }) =>
  api.post(`/step-instances/${stepId}/decision`, { decision, comment }));
export const signOff = thunk("phases/signOff", ({ id, decision, comment }) =>
  api.post(`/phase-instances/${id}/signoff`, { decision, comment }));

const NOTICE = {
  [saveValues.typePrefix]: "Draft saved",
  [submitStep.typePrefix]: "Step submitted for approval",
  [decideStep.typePrefix]: "Review recorded",
  [signOff.typePrefix]: "Sign-off recorded",
};

const slice = createSlice({
  name: "phases",
  initialState: { actions: [], instance: null, loading: false, busy: false, error: null, errors: null, notice: null },
  reducers: { clearInstance: (s) => { s.instance = null; s.error = null; s.errors = null; s.notice = null; } },
  extraReducers: (b) => {
    b.addCase(fetchActions.fulfilled, (s, a) => { s.actions = a.payload; })
      .addCase(fetchInstance.pending, (s) => { s.loading = true; s.error = null; })
      .addCase(fetchInstance.fulfilled, (s, a) => { s.loading = false; s.instance = a.payload; })
      .addCase(fetchInstance.rejected, (s, a) => { s.loading = false; s.error = errorOf(a); });
    for (const t of [saveValues, submitStep, decideStep, signOff]) {
      b.addCase(t.pending, (s) => { s.busy = true; s.error = null; s.errors = null; s.notice = null; })
        .addCase(t.fulfilled, (s, a) => { s.busy = false; s.instance = a.payload; s.notice = NOTICE[t.typePrefix]; })
        .addCase(t.rejected, (s, a) => { s.busy = false; s.error = errorOf(a); s.errors = a.payload?.errors || null; });
    }
  },
});
export const { clearInstance } = slice.actions;
export default slice.reducer;
