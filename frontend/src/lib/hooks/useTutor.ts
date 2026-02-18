"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import type { TutorMessage, TutorConversation } from "../types";

export function useTutorHistory() {
  return useQuery({
    queryKey: ["tutor", "history"],
    queryFn: () =>
      api.get<{ conversations: TutorConversation[] }>("/api/tutor/history"),
    staleTime: 2 * 60 * 1000,
  });
}

interface TutorMessageResponse {
  success: boolean;
  response: string;
  follow_ups?: string[];
}

export function useTutorChat(conversationId?: string) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");

  const sendMessage = useMutation({
    mutationFn: async ({
      message,
      subject,
      topic,
      images,
    }: {
      message: string;
      subject?: string;
      topic?: string;
      images?: string[];
    }) => {
      const userMsg: TutorMessage = {
        id: `temp-${Date.now()}`,
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
        images,
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setStreamingContent("");

      try {
        const data = await api.post<TutorMessageResponse>(
          "/api/tutor/message",
          {
            conversation_id: conversationId,
            message,
            subject,
            topic,
            images,
          }
        );

        const fullContent = data.response || "";
        setStreamingContent(fullContent);

        const assistantMsg: TutorMessage = {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: fullContent,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        return assistantMsg;
      } finally {
        setIsStreaming(false);
        setStreamingContent("");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tutor", "history"] });
    },
  });

  return {
    messages,
    setMessages,
    isStreaming,
    streamingContent,
    sendMessage: sendMessage.mutateAsync,
    isSending: sendMessage.isPending,
  };
}
