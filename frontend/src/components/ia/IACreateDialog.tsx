"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSubjects } from "@/lib/hooks/useStudy";
import { useCreateSession } from "@/lib/hooks/useIA";

interface IACreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (sessionId: number) => void;
}

export function IACreateDialog({
  open,
  onOpenChange,
  onCreated,
}: IACreateDialogProps) {
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [docType, setDocType] = useState("ia");
  const { data: subjectsData } = useSubjects();
  const createSession = useCreateSession();

  const subjects = subjectsData?.subjects ?? [];

  const handleCreate = () => {
    if (!title || !subject) return;
    createSession.mutate(
      { doc_type: docType, subject, title },
      {
        onSuccess: (data) => {
          setTitle("");
          setSubject("");
          setDocType("ia");
          onOpenChange(false);
          onCreated(data.session_id);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New IA Project</DialogTitle>
          <DialogDescription>
            Set up your Internal Assessment workspace
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              placeholder="e.g. Effect of temperature on enzyme activity"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Subject</Label>
            <Select value={subject} onValueChange={setSubject}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Choose subject" />
              </SelectTrigger>
              <SelectContent>
                {subjects.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Document Type</Label>
            <Select value={docType} onValueChange={setDocType}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ia">Internal Assessment</SelectItem>
                <SelectItem value="ee">Extended Essay</SelectItem>
                <SelectItem value="tok">TOK Essay</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={handleCreate}
            disabled={!title || !subject || createSession.isPending}
          >
            {createSession.isPending ? "Creating..." : "Create Project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
