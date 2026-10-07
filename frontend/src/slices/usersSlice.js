import { createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { thunk, errorOf } from "../thunk";

export const fetchUsers = thunk("users/list", (status) => api.get(`/users${status ? `?status=${status}` : ""}`));
export const fetchDirectory = thunk("users/directory", () => api.get("/users/directory"));
export const approveUser = thunk("users/approve", (id) => api.post(`/users/${id}/approve`));
export const patchUser = thunk("users/patch", ({ id, ...body }) => api.patch(`/users/${id}`, body));
export const resetPassword = thunk("users/reset", async (id) => ({ id, ...(await api.post(`/users/${id}/reset-password`)) }));

const replace = (list, u) => list.map((x) => (x.id === u.id ? u : x));

const slice = createSlice({
  name: "users",
  initialState: { list: [], directory: [], tempPasswords: {}, error: null, loading: false },
  reducers: {},
  extraReducers: (b) => {
    b.addCase(fetchUsers.pending, (s) => { s.loading = true; })
      .addCase(fetchUsers.fulfilled, (s, a) => { s.loading = false; s.list = a.payload; })
      .addCase(fetchUsers.rejected, (s, a) => { s.loading = false; s.error = errorOf(a); })
      .addCase(fetchDirectory.fulfilled, (s, a) => { s.directory = a.payload; })
      .addCase(approveUser.fulfilled, (s, a) => { s.list = replace(s.list, a.payload); })
      .addCase(patchUser.fulfilled, (s, a) => { s.list = replace(s.list, a.payload); })
      .addCase(patchUser.rejected, (s, a) => { s.error = errorOf(a); })
      .addCase(resetPassword.fulfilled, (s, a) => { s.tempPasswords[a.payload.id] = a.payload.temporary_password; });
  },
});
export default slice.reducer;
