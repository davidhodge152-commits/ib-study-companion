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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface PlanConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerate: (params: { days_ahead: number; daily_minutes: number }) => void;
  isPending: boolean;
}

export function PlanConfigDialog({
  open,
  onOpenChange,
  onGenerate,
  isPending,
}: PlanConfigDialogProps) {
  const [daysAhead, setDaysAhead] = useState(7);
  const [dailyMinutes, setDailyMinutes] = useState(180);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generate Study Plan</DialogTitle>
          <DialogDescription>
            Configure your weekly study plan parameters
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Plan Duration</Label>
            <Select
              value={String(daysAhead)}
              onValueChange={(v) => setDaysAhead(Number(v))}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3 days</SelectItem>
                <SelectItem value="7">1 week</SelectItem>
                <SelectItem value="14">2 weeks</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Daily Study Time</Label>
            <Select
              value={String(dailyMinutes)}
              onValueChange={(v) => setDailyMinutes(Number(v))}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="60">1 hour</SelectItem>
                <SelectItem value="120">2 hours</SelectItem>
                <SelectItem value="180">3 hours</SelectItem>
                <SelectItem value="240">4 hours</SelectItem>
                <SelectItem value="300">5 hours</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() =>
              onGenerate({
                days_ahead: daysAhead,
                daily_minutes: dailyMinutes,
              })
            }
            disabled={isPending}
          >
            {isPending ? "Generating..." : "Generate Plan"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
