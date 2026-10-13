import { configureStore } from "@reduxjs/toolkit"; // includes redux-thunk middleware by default
import auth from "./slices/authSlice";
import users from "./slices/usersSlice";
import workflows from "./slices/workflowsSlice";
import projects from "./slices/projectsSlice";
import phases from "./slices/phasesSlice";

export const store = configureStore({ reducer: { auth, users, workflows, projects, phases } });
