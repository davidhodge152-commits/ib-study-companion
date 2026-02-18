"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import type { Comment, CommunityPost, PaginatedResponse } from "../types";

export function useCommunityPosts() {
  return useInfiniteQuery({
    queryKey: ["community", "posts"],
    queryFn: ({ pageParam = 1 }) =>
      api.get<PaginatedResponse<CommunityPost>>(
        `/api/community/posts?page=${pageParam}`
      ),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.page + 1 : undefined,
    staleTime: 60 * 1000,
  });
}

export function useCreatePost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      title: string;
      content: string;
      subject: string;
    }) => api.post("/api/community/post", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["community"] });
    },
  });
}

export function useVotePost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, vote }: { postId: number; vote: 1 | -1 }) =>
      api.post(`/api/community/posts/${postId}/vote`, { vote }),
    onMutate: async ({ postId, vote }) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ["community", "posts"] });

      // Snapshot the previous value
      const previous = queryClient.getQueryData(["community", "posts"]);

      // Optimistically update the infinite query cache
      queryClient.setQueryData(
        ["community", "posts"],
        (old: { pages: PaginatedResponse<CommunityPost>[]; pageParams: unknown[] } | undefined) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((post) => {
                if (post.id !== postId) return post;

                const previousVote = post.user_vote ?? 0;
                // If the user taps the same vote direction, toggle it off
                const newVote = previousVote === vote ? 0 : vote;
                const voteDelta = newVote - previousVote;

                return {
                  ...post,
                  votes: post.votes + voteDelta,
                  user_vote: newVote as -1 | 0 | 1,
                };
              }),
            })),
          };
        }
      );

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Roll back to the previous value on error
      if (context?.previous) {
        queryClient.setQueryData(["community", "posts"], context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server state
      queryClient.invalidateQueries({ queryKey: ["community"] });
    },
  });
}

export function useComments(postId: number | null) {
  return useQuery({
    queryKey: ["community", "comments", postId],
    queryFn: () =>
      api.get<{ comments: Comment[] }>(
        `/api/community/posts/${postId}/comments`
      ),
    enabled: !!postId,
  });
}

export function useCreateComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, content }: { postId: number; content: string }) =>
      api.post(`/api/community/posts/${postId}/comments`, { content }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["community", "comments", variables.postId],
      });
      queryClient.invalidateQueries({ queryKey: ["community", "posts"] });
    },
  });
}
