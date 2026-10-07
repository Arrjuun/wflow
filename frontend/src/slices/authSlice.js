import { createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { thunk, errorOf } from "../thunk";

export const fetchMe = thunk("auth/me", async () => {
  try {
    return await api.get("/auth/me");
  } catch (e) {
    if (e.status === 401) return null;
    throw e;
  }
});
export const login = thunk("auth/login", (b) => api.post("/auth/login", b));
export const register = thunk("auth/register", (b) => api.post("/auth/register", b));
export const logout = thunk("auth/logout", () => api.post("/auth/logout"));
export const changePassword = thunk("auth/changePassword", (b) => api.post("/auth/change-password", b));

const slice = createSlice({
  name: "auth",
  initialState: { user: null, ready: false, error: null, notice: null, busy: false },
  reducers: { clearMessages: (s) => { s.error = null; s.notice = null; } },
  extraReducers: (b) => {
    b.addCase(fetchMe.fulfilled, (s, a) => { s.user = a.payload; s.ready = true; })
      .addCase(fetchMe.rejected, (s) => { s.ready = true; })
      .addCase(login.pending, (s) => { s.busy = true; s.error = null; })
      .addCase(login.fulfilled, (s, a) => { s.busy = false; s.user = a.payload; })
      .addCase(login.rejected, (s, a) => { s.busy = false; s.error = errorOf(a); })
      .addCase(register.pending, (s) => { s.busy = true; s.error = null; s.notice = null; })
      .addCase(register.fulfilled, (s, a) => { s.busy = false; s.notice = a.payload.message; })
      .addCase(register.rejected, (s, a) => { s.busy = false; s.error = errorOf(a); })
      .addCase(logout.fulfilled, (s) => { s.user = null; })
      .addCase(changePassword.pending, (s) => { s.busy = true; s.error = null; })
      .addCase(changePassword.fulfilled, (s, a) => { s.busy = false; s.user = a.payload; })
      .addCase(changePassword.rejected, (s, a) => { s.busy = false; s.error = errorOf(a); });
  },
});
export const { clearMessages } = slice.actions;
export default slice.reducer;
