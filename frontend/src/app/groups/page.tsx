"use client";

import { useState } from "react";
import { useGroups, useJoinGroup, useCreateGroup, useLeaveGroup, useDeleteGroup } from "@/lib/hooks/useGroups";
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
import { toast } from "sonner";

export default function GroupsPage() {
  const { data, isLoading, error } = useGroups();
  const joinGroup = useJoinGroup();
  const createGroup = useCreateGroup();
  const leaveGroup = useLeaveGroup();
  const deleteGroup = useDeleteGroup();

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
          toast.success("Group created!");
          setName("");
          setDescription("");
          setSubject("");
          setShowCreateForm(false);
        },
        onError: () => {
          toast.error("Failed to create group. Please try again.");
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
              <CardFooter className="flex gap-2">
                {group.is_member ? (
                  <>
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => {
                        if (window.confirm("Leave this study group?")) {
                          leaveGroup.mutate(group.id);
                        }
                      }}
                      disabled={leaveGroup.isPending}
                    >
                      {leaveGroup.isPending ? "Leaving..." : "Leave"}
                    </Button>
                    {group.is_admin && (
                      <Button
                        variant="destructive"
                        size="icon"
                        onClick={() => {
                          if (window.confirm("Delete this group permanently? All members will be removed.")) {
                            deleteGroup.mutate(group.id);
                          }
                        }}
                        disabled={deleteGroup.isPending}
                        title="Delete group"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </Button>
                    )}
                  </>
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
