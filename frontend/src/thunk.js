import { createAsyncThunk } from "@reduxjs/toolkit";

// Wraps a redux-thunk async action so failures arrive as a plain serializable payload.
export const thunk = (type, fn) =>
  createAsyncThunk(type, async (arg, { rejectWithValue }) => {
    try {
      return await fn(arg);
    } catch (e) {
      return rejectWithValue({ message: e.message, status: e.status, errors: e.errors || null });
    }
  });

export const errorOf = (action) => action.payload?.message || action.error?.message || "Something went wrong";
