"use client";

import { useState } from "react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function VerificationBanner() {
  const { user } = useAuth();
  const [sending, setSending] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Only show if user exists, email is explicitly not verified, and not dismissed
  if (!user || dismissed || user.email_verified !== false) return null;

  const handleResend = async () => {
    setSending(true);
    try {
      await api.post("/api/auth/resend-verification", { email: user.email });
      toast.success("Verification email sent! Check your inbox.");
    } catch {
      toast.error("Failed to send verification email. Try again later.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mb-4 flex items-center justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 dark:border-amber-800 dark:bg-amber-900/20">
      <p className="text-sm text-amber-700 dark:text-amber-400">
        Please verify your email address to unlock all features.
      </p>
      <div className="flex shrink-0 gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={handleResend}
          disabled={sending}
        >
          {sending ? "Sending..." : "Resend Email"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setDismissed(true)}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}
