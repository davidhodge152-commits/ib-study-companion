"use client";

import { useState, useRef, useEffect } from "react";
import { useTutorChat } from "@/lib/hooks/useTutor";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";

export default function TutorPage() {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    messages,
    isStreaming,
    streamingContent,
    sendMessage,
    isSending,
  } = useTutorChat();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;
    setInput("");
    await sendMessage({ message: trimmed });
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col space-y-4">
      <div>
        <h1 className="text-2xl font-bold">AI Tutor</h1>
        <p className="text-muted-foreground">
          Ask questions, get explanations, and deepen your IB understanding
        </p>
      </div>

      {/* Message List */}
      <Card className="flex-1 overflow-hidden">
        <CardContent className="h-full overflow-y-auto p-4">
          {messages.length === 0 && !isStreaming && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <p className="text-lg font-medium text-muted-foreground">
                  Start a conversation
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Ask about any IB topic -- your tutor supports math notation,
                  diagrams, and follow-up questions.
                </p>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <MarkdownRenderer content={msg.content} />
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  )}
                  <p className="mt-1 text-[10px] opacity-60">
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            ))}

            {/* Streaming indicator */}
            {isStreaming && streamingContent && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl bg-muted px-4 py-3">
                  <MarkdownRenderer content={streamingContent} />
                </div>
              </div>
            )}

            {isStreaming && !streamingContent && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-muted px-4 py-3">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:0ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:150ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </CardContent>
      </Card>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your tutor anything..."
          disabled={isSending}
          className="flex-1 rounded-lg border bg-background px-4 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
        />
        <Button type="submit" disabled={isSending || !input.trim()}>
          {isSending ? "Sending..." : "Send"}
        </Button>
      </form>
    </div>
  );
}
