import { create } from "zustand";

interface AuthRequiredState {
  open: boolean;
  reason: string | null;
  setOpen: (open: boolean, reason?: string | null) => void;
}

export const useAuthRequiredStore = create<AuthRequiredState>((set) => ({
  open: false,
  reason: null,
  setOpen: (open, reason = null) => set({ open, reason }),
}));

interface TaskEvent {
  kind: string;
  run_id?: number;
  target?: string;
  items?: number;
  error?: string;
  ts: number;
}

interface TaskStreamState {
  events: TaskEvent[];
  push: (e: Omit<TaskEvent, "ts">) => void;
}

export const useTaskStreamStore = create<TaskStreamState>((set) => ({
  events: [],
  push: (e) =>
    set((s) => ({ events: [{ ...e, ts: Date.now() }, ...s.events].slice(0, 200) })),
}));

interface AlertEvent {
  id: number;
  kind: string;
  severity: string;
  payload?: Record<string, unknown>;
  dispatched_at: string;
  ts: number;
}

interface AlertStreamState {
  events: AlertEvent[];
  unread: number;
  push: (e: Omit<AlertEvent, "ts">) => void;
  markRead: () => void;
}

export const useAlertStreamStore = create<AlertStreamState>((set) => ({
  events: [],
  unread: 0,
  push: (e) =>
    set((s) => ({
      events: [{ ...e, ts: Date.now() }, ...s.events].slice(0, 200),
      unread: s.unread + 1,
    })),
  markRead: () => set({ unread: 0 }),
}));
