"use client";

import { useGroups, useJoinGroup } from "@/lib/hooks/useGroups";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

export default function GroupsPage() {
  const { data, isLoading, error } = useGroups();
  const joinGroup = useJoinGroup();

  if (isLoading) return <LoadingSkeleton variant="card" count={6} />;

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load study groups. Please try refreshing.
        </p>
      </div>
    );
  }

  const groups = data?.groups ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Study Groups</h1>
        <p className="text-muted-foreground">
          Join study groups to collaborate with other IB students
        </p>
      </div>

      {groups.length === 0 ? (
        <EmptyState
          title="No study groups available"
          description="Be the first to create a study group and invite your classmates."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groups.map((group) => (
            <Card
              key={group.id}
              className="transition-shadow hover:shadow-md"
            >
              <CardHeader>
                <CardTitle className="text-lg">{group.name}</CardTitle>
                <CardDescription>{group.subject}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {group.description}
                </p>
                <p className="mt-3 text-xs text-muted-foreground">
                  {group.member_count}{" "}
                  {group.member_count === 1 ? "member" : "members"}
                </p>
              </CardContent>
              <CardFooter>
                {group.is_member ? (
                  <Button variant="secondary" className="w-full" disabled>
                    Joined
                  </Button>
                ) : (
                  <Button
                    className="w-full"
                    onClick={() => joinGroup.mutate(group.id)}
                    disabled={joinGroup.isPending}
                  >
                    {joinGroup.isPending ? "Joining..." : "Join Group"}
                  </Button>
                )}
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
