"use client";

import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api-client";
import type { CommunityPost, PaginatedResponse } from "../types";

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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["community"] });
    },
  });
}
