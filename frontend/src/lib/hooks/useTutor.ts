"use client";

import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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

export function useTutorChat(conversationId?: string) {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<TutorMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [isSending, setIsSending] = useState(false);

  const sendMessage = useCallback(
    async ({
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
      setIsSending(true);
      setStreamingContent("");
      setFollowUps([]);

      let fullContent = "";

      try {
        // Use SSE streaming endpoint
        const stream = await api.stream("/api/tutor/message/stream", {
          conversation_id: conversationId,
          message,
          subject,
          topic,
          images,
        });

        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split("\n");
          // Keep incomplete last line in buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "chunk") {
                fullContent += event.content;
                setStreamingContent(fullContent);
              } else if (event.type === "done") {
                if (event.follow_ups?.length) {
                  setFollowUps(event.follow_ups);
                }
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      } catch {
        // Fallback: if streaming fails, use the regular POST endpoint
        try {
          const data = await api.post<{
            success: boolean;
            response: string;
            follow_ups?: string[];
          }>("/api/tutor/message", {
            conversation_id: conversationId,
            message,
            subject,
            topic,
            images,
          });
          fullContent = data.response || "";
          setStreamingContent(fullContent);
          if (data.follow_ups?.length) {
            setFollowUps(data.follow_ups);
          }
        } catch {
          fullContent =
            "Failed to get a response. Please check your connection and try again.";
          setStreamingContent(fullContent);
        }
      }

      // Add assistant message
      const assistantMsg: TutorMessage = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: fullContent,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsStreaming(false);
      setStreamingContent("");
      setIsSending(false);

      queryClient.invalidateQueries({ queryKey: ["tutor", "history"] });
      return assistantMsg;
    },
    [conversationId, queryClient]
  );

  return {
    messages,
    setMessages,
    isStreaming,
    streamingContent,
    followUps,
    sendMessage,
    isSending,
  };
}
