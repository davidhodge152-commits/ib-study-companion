"use client";

import { create } from "zustand";

export interface AppNotification {
  id: number;
  message: string;
  type: "info" | "success" | "warning" | "study_reminder" | "streak";
  read: boolean;
  created_at: string;
  link?: string;
}

interface NotificationState {
  notifications: AppNotification[];
  panelOpen: boolean;
  unreadCount: number;
  setNotifications: (n: AppNotification[]) => void;
  addNotification: (n: AppNotification) => void;
  markAllRead: () => void;
  togglePanel: () => void;
  setPanelOpen: (open: boolean) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  panelOpen: false,
  unreadCount: 0,
  setNotifications: (notifications) =>
    set({
      notifications,
      unreadCount: notifications.filter((n) => !n.read).length,
    }),
  addNotification: (n) =>
    set((state) => {
      const notifications = [n, ...state.notifications];
      return {
        notifications,
        unreadCount: notifications.filter((x) => !x.read).length,
      };
    }),
  markAllRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
  togglePanel: () => set((state) => ({ panelOpen: !state.panelOpen })),
  setPanelOpen: (panelOpen) => set({ panelOpen }),
}));
