"use client";

import { useState } from "react";
import { useGroups, useJoinGroup, useCreateGroup } from "@/lib/hooks/useGroups";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

export default function GroupsPage() {
  const { data, isLoading, error } = useGroups();
  const joinGroup = useJoinGroup();
  const createGroup = useCreateGroup();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [subject, setSubject] = useState("");

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !subject.trim()) return;
    createGroup.mutate(
      { name: name.trim(), description: description.trim(), subject: subject.trim() },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
          setSubject("");
          setShowCreateForm(false);
        },
      }
    );
  }

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Study Groups</h1>
          <p className="text-muted-foreground">
            Join study groups to collaborate with other IB students
          </p>
        </div>
        <Button
          onClick={() => setShowCreateForm((prev) => !prev)}
          variant={showCreateForm ? "outline" : "default"}
        >
          {showCreateForm ? "Cancel" : "Create Group"}
        </Button>
      </div>

      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create a New Study Group</CardTitle>
            <CardDescription>
              Set up a group for your subject and invite classmates to join.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="group-name">Group Name</Label>
                <Input
                  id="group-name"
                  placeholder="e.g. HL Biology Study Group"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="group-subject">Subject</Label>
                <Input
                  id="group-subject"
                  placeholder="e.g. Biology HL"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="group-description">Description</Label>
                <Input
                  id="group-description"
                  placeholder="What will this group focus on?"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createGroup.isPending}>
                  {createGroup.isPending ? "Creating..." : "Create Group"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </Button>
              </div>
              {createGroup.isError && (
                <p className="text-sm text-destructive">
                  Failed to create group. Please try again.
                </p>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      {groups.length === 0 ? (
        <EmptyState
          title="No study groups available"
          description="Be the first to create a study group and invite your classmates."
          action={
            !showCreateForm ? (
              <Button onClick={() => setShowCreateForm(true)}>
                Create Your First Group
              </Button>
            ) : undefined
          }
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
