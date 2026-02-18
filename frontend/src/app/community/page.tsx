"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  useCommunityPosts,
  useCreatePost,
  useVotePost,
  useReportPost,
  useDeletePost,
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
import { CommentThread } from "@/components/community/CommentThread";
import { useSubjects } from "@/lib/hooks/useStudy";
import { useAuth } from "@/lib/hooks/useAuth";
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
  const reportPost = useReportPost();
  const deletePost = useDeletePost();
  const { data: subjectsData } = useSubjects();
  const { user } = useAuth();
  const subjects = subjectsData?.subjects ?? [];

  // Create post form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newSubject, setNewSubject] = useState("");

  // Track which post has its comments expanded
  const [expandedPost, setExpandedPost] = useState<number | null>(null);

  // Report modal state
  const [reportingPostId, setReportingPostId] = useState<number | null>(null);
  const [reportReason, setReportReason] = useState("");

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

                  {/* Comment toggle */}
                  <button
                    onClick={() =>
                      setExpandedPost(
                        expandedPost === post.id ? null : post.id
                      )
                    }
                    className={`flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:bg-muted ${
                      expandedPost === post.id
                        ? "text-primary"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
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
                        d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
                      />
                    </svg>
                    {post.comment_count}{" "}
                    {post.comment_count === 1 ? "comment" : "comments"}
                  </button>

                  {/* Report button */}
                  <button
                    onClick={() => {
                      setReportingPostId(post.id);
                      setReportReason("");
                    }}
                    className="flex items-center gap-1 rounded px-1 py-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    aria-label="Report post"
                    title="Report post"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l.108.054a9 9 0 0 0 6.086.71l3.114-.732a48.524 48.524 0 0 1-.005-10.499l-3.11.732a9 9 0 0 1-6.085-.711l-.108-.054a9 9 0 0 0-6.208-.682L3 4.5M3 15V4.5" />
                    </svg>
                    Report
                  </button>

                  {/* Delete button — only for post author */}
                  {user && post.author_id === user.id && (
                    <button
                      onClick={() => {
                        if (window.confirm("Delete this post? This cannot be undone.")) {
                          deletePost.mutate(post.id);
                        }
                      }}
                      className="flex items-center gap-1 rounded px-1 py-0.5 text-destructive transition-colors hover:bg-destructive/10"
                      aria-label="Delete post"
                      title="Delete your post"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                      Delete
                    </button>
                  )}
                </div>

                {/* Expanded comment thread */}
                {expandedPost === post.id && (
                  <div className="mt-4">
                    <CommentThread postId={post.id} />
                  </div>
                )}
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

      {/* Report dialog */}
      {reportingPostId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="mx-4 w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-base">Report Post</CardTitle>
              <CardDescription>
                Help us keep the community safe. Tell us why this post should be
                reviewed.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {[
                    "Spam or advertising",
                    "Inappropriate content",
                    "Incorrect information",
                    "Harassment",
                  ].map((reason) => (
                    <button
                      key={reason}
                      onClick={() => setReportReason(reason)}
                      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                        reportReason === reason
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground hover:border-primary/50"
                      }`}
                    >
                      {reason}
                    </button>
                  ))}
                </div>
                <Textarea
                  placeholder="Add more details (optional)..."
                  value={
                    [
                      "Spam or advertising",
                      "Inappropriate content",
                      "Incorrect information",
                      "Harassment",
                    ].includes(reportReason)
                      ? ""
                      : reportReason
                  }
                  onChange={(e) => setReportReason(e.target.value)}
                  rows={2}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    variant="ghost"
                    onClick={() => setReportingPostId(null)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={!reportReason.trim() || reportPost.isPending}
                    onClick={() => {
                      reportPost.mutate(
                        {
                          postId: reportingPostId,
                          reason: reportReason.trim(),
                        },
                        {
                          onSuccess: () => setReportingPostId(null),
                        }
                      );
                    }}
                  >
                    {reportPost.isPending ? "Submitting..." : "Submit Report"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
