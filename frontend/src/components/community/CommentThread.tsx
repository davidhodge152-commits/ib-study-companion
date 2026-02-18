"use client";

import { useState } from "react";
import { useComments, useCreateComment } from "@/lib/hooks/useCommunity";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

interface CommentThreadProps {
  postId: number;
}

export function CommentThread({ postId }: CommentThreadProps) {
  const { data, isLoading } = useComments(postId);
  const createComment = useCreateComment();
  const [content, setContent] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    try {
      await createComment.mutateAsync({ postId, content: content.trim() });
      setContent("");
      toast.success("Comment posted!");
    } catch {
      toast.error("Failed to post comment.");
    }
  };

  const comments = data?.comments ?? [];

  return (
    <div className="space-y-3 border-t pt-3">
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-muted" />
          ))}
        </div>
      ) : comments.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No comments yet. Be the first!
        </p>
      ) : (
        <div className="space-y-2">
          {comments.map((c) => (
            <div key={c.id} className="rounded-md bg-muted/50 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium">{c.author_name}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(c.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className="mt-0.5 text-sm">{c.content}</p>
            </div>
          ))}
        </div>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Textarea
          placeholder="Write a comment..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={1}
          className="min-h-[36px] resize-none text-sm"
        />
        <Button
          type="submit"
          size="sm"
          disabled={createComment.isPending || !content.trim()}
        >
          Post
        </Button>
      </form>
    </div>
  );
}
