"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTutorChat, useTutorHistory } from "@/lib/hooks/useTutor";
import { useSubjects, useTopics } from "@/lib/hooks/useStudy";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MarkdownRenderer } from "@/components/shared/MarkdownRenderer";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";

export default function TutorPage() {
  const [input, setInput] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<
    string | undefined
  >(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    setMessages,
    isStreaming,
    streamingContent,
    followUps,
    sendMessage,
    isSending,
  } = useTutorChat(activeConversationId);

  // Subject/topic data
  const { data: subjectsData, isLoading: subjectsLoading } = useSubjects();
  const { data: topicsData, isLoading: topicsLoading } =
    useTopics(selectedSubject);

  // Conversation history
  const { data: historyData, isLoading: historyLoading } = useTutorHistory();

  const subjects = subjectsData?.subjects ?? [];
  const topics = topicsData?.topics ?? [];
  const conversations = historyData?.conversations ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Reset topic when subject changes
  useEffect(() => {
    setSelectedTopic("");
  }, [selectedSubject]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;
    setInput("");
    await sendMessage({
      message: trimmed,
      subject: selectedSubject || undefined,
      topic: selectedTopic || undefined,
    });
  }

  function handleFollowUpClick(followUp: string) {
    if (isSending) return;
    sendMessage({
      message: followUp,
      subject: selectedSubject || undefined,
      topic: selectedTopic || undefined,
    });
  }

  function handleLoadConversation(conversationId: string) {
    const conversation = conversations.find((c) => c.id === conversationId);
    if (!conversation) return;

    setActiveConversationId(conversationId);
    setMessages(conversation.messages ?? []);
    if (conversation.subject) setSelectedSubject(conversation.subject);
    if (conversation.topic) setSelectedTopic(conversation.topic);

    // Close sidebar on mobile after selection
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  }

  function handleNewConversation() {
    setActiveConversationId(undefined);
    setMessages([]);
    setSelectedSubject("");
    setSelectedTopic("");
  }

  function getConversationPreview(messages?: { content: string; role?: string }[]) {
    if (!messages || messages.length === 0) return "Empty conversation";
    const firstUserMsg = messages.find((m) => m.role === "user");
    if (!firstUserMsg) return "Empty conversation";
    return firstUserMsg.content.length > 60
      ? firstUserMsg.content.slice(0, 60) + "..."
      : firstUserMsg.content;
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Conversation History Sidebar */}
      <div
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        } fixed inset-y-0 left-0 z-30 w-72 border-r bg-background transition-transform md:static md:z-auto md:block md:w-64 md:shrink-0`}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b p-3">
            <h2 className="text-sm font-semibold">Conversations</h2>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNewConversation}
                title="New conversation"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 4.5v15m7.5-7.5h-15"
                  />
                </svg>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="md:hidden"
                onClick={() => setSidebarOpen(false)}
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </Button>
            </div>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-2">
              {historyLoading ? (
                <LoadingSkeleton variant="list" count={4} />
              ) : conversations.length === 0 ? (
                <p className="px-2 py-8 text-center text-xs text-muted-foreground">
                  No past conversations yet. Start chatting to build your
                  history.
                </p>
              ) : (
                <div className="space-y-1">
                  {conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => handleLoadConversation(conv.id)}
                      className={`w-full rounded-lg px-3 py-2 text-left transition-colors hover:bg-muted ${
                        activeConversationId === conv.id
                          ? "bg-muted ring-1 ring-primary/20"
                          : ""
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {conv.subject && (
                          <Badge variant="secondary" className="text-[10px]">
                            {conv.subject}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-foreground line-clamp-2">
                        {getConversationPreview(conv.messages ?? [])}
                      </p>
                      <p className="mt-1 text-[10px] text-muted-foreground">
                        {new Date(conv.created_at).toLocaleDateString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Chat Area */}
      <div className="flex min-w-0 flex-1 flex-col space-y-3">
        {/* Header with sidebar toggle */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                />
              </svg>
            </Button>
            <div>
              <h1 className="text-2xl font-bold">AI Tutor</h1>
              <p className="text-sm text-muted-foreground">
                Ask questions, get explanations, and deepen your IB
                understanding
              </p>
            </div>
          </div>
        </div>

        {/* Subject/Topic Picker */}
        <div className="flex flex-wrap items-center gap-2">
          <Select value={selectedSubject} onValueChange={setSelectedSubject}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select subject" />
            </SelectTrigger>
            <SelectContent>
              {subjectsLoading ? (
                <SelectItem value="__loading" disabled>
                  Loading...
                </SelectItem>
              ) : subjects.length === 0 ? (
                <SelectItem value="__empty" disabled>
                  No subjects available
                </SelectItem>
              ) : (
                subjects.map((subject) => (
                  <SelectItem key={subject} value={subject}>
                    {subject}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

          <Select
            value={selectedTopic}
            onValueChange={setSelectedTopic}
            disabled={!selectedSubject}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue
                placeholder={
                  selectedSubject ? "Select topic" : "Pick a subject first"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {topicsLoading ? (
                <SelectItem value="__loading" disabled>
                  Loading topics...
                </SelectItem>
              ) : topics.length === 0 ? (
                <SelectItem value="__empty" disabled>
                  No topics available
                </SelectItem>
              ) : (
                topics.map((topic) => (
                  <SelectItem key={topic} value={topic}>
                    {topic}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

          {(selectedSubject || selectedTopic) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedSubject("");
                setSelectedTopic("");
              }}
              className="text-xs text-muted-foreground"
            >
              Clear filters
            </Button>
          )}
        </div>

        {/* Message List */}
        <Card className="flex-1 overflow-hidden">
          <CardContent className="h-full overflow-y-auto p-4">
            {messages.length === 0 && !isStreaming && (
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <svg
                      className="h-8 w-8 text-muted-foreground"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342M6.75 15a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm0 0v-3.675A55.378 55.378 0 0 1 12 8.443m-7.007 11.55A5.981 5.981 0 0 0 6.75 15.75v-1.5"
                      />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-muted-foreground">
                    Start a conversation
                  </p>
                  <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                    Ask about any IB topic -- your tutor supports math notation,
                    diagrams, and follow-up questions.
                  </p>
                  {selectedSubject && (
                    <p className="mt-2 text-sm text-primary">
                      Asking about: {selectedSubject}
                      {selectedTopic ? ` / ${selectedTopic}` : ""}
                    </p>
                  )}
                </div>
              </div>
            )}

            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div key={msg.id}>
                  <div
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
                        <p className="text-sm whitespace-pre-wrap">
                          {msg.content}
                        </p>
                      )}
                      <p className="mt-1 text-[10px] opacity-60">
                        {new Date(msg.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>

                  {/* Follow-up chips after the last assistant message */}
                  {msg.role === "assistant" &&
                    idx === messages.length - 1 &&
                    !isStreaming &&
                    followUps.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2 pl-2">
                        {followUps.map((followUp, fuIdx) => (
                          <button
                            key={fuIdx}
                            onClick={() => handleFollowUpClick(followUp)}
                            disabled={isSending}
                            className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
                          >
                            {followUp}
                          </button>
                        ))}
                      </div>
                    )}
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
            placeholder={
              selectedSubject
                ? `Ask about ${selectedSubject}${selectedTopic ? ` / ${selectedTopic}` : ""}...`
                : "Ask your tutor anything..."
            }
            disabled={isSending}
            className="flex-1 rounded-lg border bg-background px-4 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          />
          <Button type="submit" disabled={isSending || !input.trim()}>
            {isSending ? "Sending..." : "Send"}
          </Button>
        </form>
      </div>
    </div>
  );
}
