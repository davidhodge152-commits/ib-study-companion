"use client";

import { useEffect, useRef, useCallback } from "react";
import { useCommunityPosts } from "@/lib/hooks/useCommunity";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

export default function CommunityPage() {
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useCommunityPosts();

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

  const posts = data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Community</h1>
        <p className="text-muted-foreground">
          Discuss topics, share resources, and help fellow IB students
        </p>
      </div>

      {posts.length === 0 ? (
        <EmptyState
          title="No posts yet"
          description="Be the first to start a discussion in the community."
        />
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Card key={post.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{post.title}</CardTitle>
                    <CardDescription>
                      {post.author} -- {post.subject} --{" "}
                      {new Date(post.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                  <span className="rounded bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                    {post.subject}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {post.content}
                </p>
                <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
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
                        d="M4.5 15.75l7.5-7.5 7.5 7.5"
                      />
                    </svg>
                    {post.votes}
                  </span>
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
