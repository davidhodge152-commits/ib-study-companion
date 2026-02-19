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
import { Textarea } from "@/components/ui/textarea";
import { useReprioritize } from "@/lib/hooks/useAdaptivePlanner";

interface ReprioritizeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ReprioritizeDialog({
  open,
  onOpenChange,
}: ReprioritizeDialogProps) {
  const [event, setEvent] = useState("");
  const reprioritize = useReprioritize();

  const handleSubmit = () => {
    if (!event.trim()) return;
    reprioritize.mutate(event, {
      onSuccess: () => {
        setEvent("");
        onOpenChange(false);
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reprioritize Study Plan</DialogTitle>
          <DialogDescription>
            Tell the AI what changed and it will adjust your priorities
          </DialogDescription>
        </DialogHeader>
        <Textarea
          placeholder="e.g. My Biology IA deadline moved to next Friday, and I have a Math test tomorrow..."
          value={event}
          onChange={(e) => setEvent(e.target.value)}
          className="min-h-[120px]"
        />
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!event.trim() || reprioritize.isPending}
          >
            {reprioritize.isPending ? "Reprioritizing..." : "Reprioritize"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
