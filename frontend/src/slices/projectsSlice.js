import { createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { thunk, errorOf } from "../thunk";

export const fetchProjects = thunk("projects/list", (archived = false) => api.get(`/projects?archived=${archived}`));
export const fetchProject = thunk("projects/get", (id) => api.get(`/projects/${id}`));
export const createProject = thunk("projects/create", (b) => api.post("/projects", b));
export const updateDetails = thunk("projects/details", ({ id, ...b }) => api.patch(`/projects/${id}`, b));
export const setMembers = thunk("projects/members", ({ id, members }) => api.put(`/projects/${id}/members`, { members }));
export const addReference = thunk("projects/addRef", async ({ id, ...b }) => {
  await api.post(`/projects/${id}/references`, b);
  return api.get(`/projects/${id}`);
});
export const deleteReference = thunk("projects/delRef", async ({ id, refId }) => {
  await api.del(`/projects/${id}/references/${refId}`);
  return api.get(`/projects/${id}`);
});
export const addLesson = thunk("projects/addLesson", async ({ id, ...b }) => {
  await api.post(`/projects/${id}/lessons`, b);
  return api.get(`/projects/${id}`);
});
export const deleteLesson = thunk("projects/delLesson", async ({ id, lessonId }) => {
  await api.del(`/projects/${id}/lessons/${lessonId}`);
  return api.get(`/projects/${id}`);
});
export const archiveProject = thunk("projects/archive", (id) => api.post(`/projects/${id}/archive`));
export const unarchiveProject = thunk("projects/unarchive", (id) => api.post(`/projects/${id}/unarchive`));

const slice = createSlice({
  name: "projects",
  initialState: { list: [], current: null, loading: false, busy: false, error: null, errors: null },
  reducers: { clearProjectError: (s) => { s.error = null; s.errors = null; } },
  extraReducers: (b) => {
    b.addCase(fetchProjects.pending, (s) => { s.loading = true; })
      .addCase(fetchProjects.fulfilled, (s, a) => { s.loading = false; s.list = a.payload; })
      .addCase(fetchProjects.rejected, (s, a) => { s.loading = false; s.error = errorOf(a); })
      .addCase(fetchProject.pending, (s) => { s.loading = true; })
      .addCase(fetchProject.fulfilled, (s, a) => { s.loading = false; s.current = a.payload; })
      .addCase(fetchProject.rejected, (s, a) => { s.loading = false; s.error = errorOf(a); });
    for (const t of [createProject, updateDetails, setMembers, addReference, deleteReference, addLesson, deleteLesson, archiveProject, unarchiveProject]) {
      b.addCase(t.pending, (s) => { s.busy = true; s.error = null; s.errors = null; })
        .addCase(t.fulfilled, (s, a) => { s.busy = false; s.current = a.payload; })
        .addCase(t.rejected, (s, a) => { s.busy = false; s.error = errorOf(a); s.errors = a.payload?.errors || null; });
    }
  },
});
export const { clearProjectError } = slice.actions;
export default slice.reducer;
