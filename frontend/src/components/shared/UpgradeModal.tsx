"use client";

import Link from "next/link";
import { useUIStore } from "@/lib/stores/ui-store";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function UpgradeModal() {
  const { upgradeModal, hideUpgradeModal } = useUIStore();
  const { open, type, planName } = upgradeModal;

  const isCredits = type === "credits";
  const title = isCredits ? "Insufficient Credits" : "Upgrade Required";
  const message = isCredits
    ? "You don't have enough credits for this action. Purchase more credits or upgrade your plan for higher limits."
    : `This feature requires the ${planName ?? "Pro"} plan or higher.`;
  const btnText = isCredits ? "Buy Credits" : "View Plans";

  return (
    <Dialog open={open} onOpenChange={(o) => !o && hideUpgradeModal()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{message}</DialogDescription>
        </DialogHeader>
        <div className="flex gap-3 pt-2">
          <Button asChild className="flex-1">
            <Link href="/pricing">{btnText}</Link>
          </Button>
          <Button variant="outline" onClick={hideUpgradeModal}>
            Dismiss
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
