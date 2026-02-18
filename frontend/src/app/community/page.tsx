"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  useCommunityPosts,
  useCreatePost,
  useVotePost,
} from "@/lib/hooks/useCommunity";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { useSubjects } from "@/lib/hooks/useStudy";
import { toast } from "sonner";
import type { CommunityPost } from "@/lib/types";

export default function CommunityPage() {
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useCommunityPosts();

  const createPost = useCreatePost();
  const votePost = useVotePost();
  const { data: subjectsData } = useSubjects();
  const subjects = subjectsData?.subjects ?? [];

  // Create post form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newSubject, setNewSubject] = useState("");

  const observerRef = useRef<HTMLDivElement>(null);

  const handleObserver = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage]
  );

  useEffect(() => {
    const node = observerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(handleObserver, {
      rootMargin: "200px",
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [handleObserver]);

  async function handleCreatePost(e: React.FormEvent) {
    e.preventDefault();
    const trimmedTitle = newTitle.trim();
    const trimmedContent = newContent.trim();
    if (!trimmedTitle || !trimmedContent || !newSubject) return;

    try {
      await createPost.mutateAsync({
        title: trimmedTitle,
        content: trimmedContent,
        subject: newSubject,
      });
      toast.success("Post created!");

      // Reset form
      setNewTitle("");
      setNewContent("");
      setNewSubject("");
      setShowCreateForm(false);
    } catch {
      toast.error("Failed to create post. Please try again.");
    }
  }

  function handleVote(postId: number, vote: 1 | -1, currentVote?: -1 | 0 | 1) {
    // If the user already voted with the same value, we still send the request
    // to let the backend handle toggling. The vote count updates optimistically
    // via onMutate in useVotePost and rolls back automatically on error.
    votePost.mutate(
      { postId, vote },
      {
        onError: () => {
          toast.error("Failed to register vote. Please try again.");
        },
      }
    );
  }

  if (isLoading) return <LoadingSkeleton variant="list" count={5} />;

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load community posts. Please try refreshing.
        </p>
      </div>
    );
  }

  const posts: CommunityPost[] =
    data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Community</h1>
          <p className="text-muted-foreground">
            Discuss topics, share resources, and help fellow IB students
          </p>
        </div>
        <Button
          onClick={() => setShowCreateForm(!showCreateForm)}
          variant={showCreateForm ? "outline" : "default"}
        >
          {showCreateForm ? "Cancel" : "New Post"}
        </Button>
      </div>

      {/* Create Post Inline Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create a New Post</CardTitle>
            <CardDescription>
              Share a question, resource, or discussion topic with the community.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreatePost} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="post-title">Title</Label>
                <Input
                  id="post-title"
                  placeholder="What's your post about?"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  required
                  maxLength={200}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="post-subject">Subject</Label>
                <Select value={newSubject} onValueChange={setNewSubject}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a subject" />
                  </SelectTrigger>
                  <SelectContent>
                    {subjects.length === 0 ? (
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
              </div>

              <div className="space-y-2">
                <Label htmlFor="post-content">Content</Label>
                <Textarea
                  id="post-content"
                  placeholder="Write your post content here..."
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  required
                  rows={4}
                  className="min-h-[120px]"
                />
              </div>

              <div className="flex items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowCreateForm(false);
                    setNewTitle("");
                    setNewContent("");
                    setNewSubject("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createPost.isPending ||
                    !newTitle.trim() ||
                    !newContent.trim() ||
                    !newSubject
                  }
                >
                  {createPost.isPending ? "Posting..." : "Post"}
                </Button>
              </div>

              {createPost.isError && (
                <p className="text-sm text-destructive">
                  Failed to create post. Please try again.
                </p>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      {/* Posts Feed */}
      {posts.length === 0 ? (
        <EmptyState
          title="No posts yet"
          description="Be the first to start a discussion in the community."
          action={
            !showCreateForm ? (
              <Button onClick={() => setShowCreateForm(true)}>
                Create the first post
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Card key={post.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="text-base">{post.title}</CardTitle>
                    <CardDescription>
                      {post.author} -- {post.subject} --{" "}
                      {new Date(post.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                  <span className="ml-2 shrink-0 rounded bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                    {post.subject}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {post.content}
                </p>
                <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                  {/* Voting controls */}
                  <div className="flex items-center gap-0.5">
                    <button
                      onClick={() =>
                        handleVote(post.id, 1, post.user_vote)
                      }

                      className={`rounded p-1 transition-colors hover:bg-muted ${
                        post.user_vote === 1
                          ? "text-primary"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      aria-label="Upvote"
                    >
                      <svg
                        className="h-4 w-4"
                        fill={post.user_vote === 1 ? "currentColor" : "none"}
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={post.user_vote === 1 ? 0 : 1.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M4.5 15.75l7.5-7.5 7.5 7.5"
                        />
                      </svg>
                    </button>
                    <span
                      className={`min-w-[1.5rem] text-center text-sm font-medium ${
                        post.user_vote === 1
                          ? "text-primary"
                          : post.user_vote === -1
                            ? "text-destructive"
                            : "text-muted-foreground"
                      }`}
                    >
                      {post.votes}
                    </span>
                    <button
                      onClick={() =>
                        handleVote(post.id, -1, post.user_vote)
                      }

                      className={`rounded p-1 transition-colors hover:bg-muted ${
                        post.user_vote === -1
                          ? "text-destructive"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      aria-label="Downvote"
                    >
                      <svg
                        className="h-4 w-4"
                        fill={post.user_vote === -1 ? "currentColor" : "none"}
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={post.user_vote === -1 ? 0 : 1.5}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                        />
                      </svg>
                    </button>
                  </div>

                  {/* Comment count */}
                  <span className="flex items-center gap-1">
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
                        d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
                      />
                    </svg>
                    {post.comment_count}{" "}
                    {post.comment_count === 1 ? "comment" : "comments"}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Infinite scroll sentinel */}
          <div ref={observerRef} className="py-4 text-center">
            {isFetchingNextPage && (
              <LoadingSkeleton variant="list" count={2} />
            )}
            {!hasNextPage && posts.length > 0 && (
              <p className="text-sm text-muted-foreground">
                You have reached the end of the feed.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
