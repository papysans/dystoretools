import { create } from "zustand";
import type { LocalUser } from "../api/auth";

interface AuthState {
  user: LocalUser | null;
  checked: boolean;
  setUser: (user: LocalUser | null) => void;
  setChecked: (checked: boolean) => void;
  hasPermission: (permission: string) => boolean;
}

export const useLocalAuthStore = create<AuthState>((set, get) => ({
  user: null,
  checked: false,
  setUser: (user) => set({ user }),
  setChecked: (checked) => set({ checked }),
  hasPermission: (permission) => {
    const user = get().user;
    if (!user) return false;
    return user.permissions.includes("*") || user.permissions.includes(permission);
  },
}));
