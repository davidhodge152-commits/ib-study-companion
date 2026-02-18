"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, Loader2, ArrowLeft, CheckCircle } from "lucide-react";
import { forgotPassword } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");
    const result = await forgotPassword(email);
    setIsSubmitting(false);
    if (result.success) {
      setSent(true);
    } else {
      setError(result.error ?? "Failed to send reset email");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600">
            <BookOpen className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Reset your password</h1>
          <p className="mt-1 text-muted-foreground">
            Enter your email and we&apos;ll send you a reset link
          </p>
        </div>

        {sent ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 pt-6 text-center">
              <CheckCircle className="h-12 w-12 text-success-500" />
              <p className="text-sm text-muted-foreground">
                If an account with that email exists, we&apos;ve sent a password
                reset link.
              </p>
              <Button asChild variant="outline">
                <Link href="/login">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to login
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            {error && (
              <div className="mb-4 rounded-lg border border-danger-500/20 bg-danger-50 p-3 dark:bg-danger-500/10" role="alert">
                <p className="text-sm text-danger-700 dark:text-danger-500">{error}</p>
              </div>
            )}
            <Card>
              <CardContent className="space-y-4 pt-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="your@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Send Reset Link
                  </Button>
                </form>
              </CardContent>
            </Card>
            <p className="mt-4 text-center text-sm text-muted-foreground">
              <Link href="/login" className="text-primary hover:underline">
                <ArrowLeft className="mr-1 inline h-3 w-3" />
                Back to login
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
