"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { BookOpen, Loader2, CheckCircle } from "lucide-react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const userId = searchParams.get("id") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("/api/auth/reset-password", { id: userId, token, password });
      setDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary">
            <BookOpen className="h-8 w-8 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold">Set new password</h1>
        </div>

        {done ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 pt-6 text-center">
              <CheckCircle className="h-12 w-12 text-success-500" />
              <p className="font-medium">Password reset successfully!</p>
              <Button asChild>
                <Link href="/login">Sign in</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            {error && (
              <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/5 p-3" role="alert">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}
            <Card>
              <CardContent className="space-y-4 pt-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="password">New Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="At least 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      placeholder="Confirm new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Reset Password
                  </Button>
                </form>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
