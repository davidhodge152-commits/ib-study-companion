"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "../api-client";
import {
  useNotificationStore,
  type AppNotification,
} from "../stores/notification-store";

export function useNotifications() {
  const store = useNotificationStore();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["notifications"],
    queryFn: () =>
      api.get<{ notifications: AppNotification[] }>("/api/notifications"),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  useEffect(() => {
    if (query.data?.notifications) {
      store.setNotifications(query.data.notifications);
    }
  }, [query.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const markAllRead = useMutation({
    mutationFn: () => api.post("/api/notifications/read-all"),
    onSuccess: () => {
      store.markAllRead();
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return {
    notifications: store.notifications,
    unreadCount: store.unreadCount,
    panelOpen: store.panelOpen,
    togglePanel: store.togglePanel,
    setPanelOpen: store.setPanelOpen,
    markAllRead: markAllRead.mutateAsync,
    isLoading: query.isLoading,
  };
}
