"use client";

import { useState } from "react";
import Link from "next/link";
import { BookOpen, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

export function RegisterForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [clientError, setClientError] = useState("");
  const { register, registerError, isRegistering } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientError("");

    if (password !== confirmPassword) {
      setClientError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setClientError("Password must be at least 8 characters");
      return;
    }

    await register({ name, email, password });
  };

  const error = clientError || registerError;

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600">
            <BookOpen className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Create your account</h1>
          <p className="mt-1 text-muted-foreground">
            Start your IB exam preparation journey
          </p>
        </div>

        {error && (
          <div
            className="mb-4 rounded-lg border border-danger-500/20 bg-danger-50 p-3 dark:bg-danger-500/10"
            role="alert"
          >
            <p className="text-sm text-danger-700 dark:text-danger-500">
              {error}
            </p>
          </div>
        )}

        <Card>
          <CardContent className="space-y-4 pt-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  autoComplete="name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                />
              </div>
              <Button type="submit" className="w-full" disabled={isRegistering}>
                {isRegistering ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Create Account
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:underline"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
