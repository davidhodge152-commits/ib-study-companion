"use client";

import { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function AccountPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleProfileSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    // TODO: call api.patch("/api/account/profile", { name, email })
    setTimeout(() => setSaving(false), 500);
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword !== confirmPassword) return;
    setSaving(true);
    // TODO: call api.post("/api/account/change-password", { currentPassword, newPassword })
    setTimeout(() => {
      setSaving(false);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    }, 500);
  }

  const inputClasses =
    "w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-primary/50 disabled:opacity-50";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Account</h1>
        <p className="text-muted-foreground">
          Manage your profile and account settings
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Profile Form */}
        <Card>
          <form onSubmit={handleProfileSubmit}>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>
                Update your name and email address
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label
                  htmlFor="name"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your full name"
                  className={inputClasses}
                />
              </div>
              <div>
                <label
                  htmlFor="email"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={inputClasses}
                />
              </div>
            </CardContent>
            <CardFooter>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        {/* Password Form */}
        <Card>
          <form onSubmit={handlePasswordSubmit}>
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label
                  htmlFor="current-password"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Current Password
                </label>
                <input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  className={inputClasses}
                />
              </div>
              <div>
                <label
                  htmlFor="new-password"
                  className="mb-1.5 block text-sm font-medium"
                >
                  New Password
                </label>
                <input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  className={inputClasses}
                />
              </div>
              <div>
                <label
                  htmlFor="confirm-password"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Confirm New Password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  className={inputClasses}
                />
                {newPassword &&
                  confirmPassword &&
                  newPassword !== confirmPassword && (
                    <p className="mt-1 text-xs text-destructive">
                      Passwords do not match
                    </p>
                  )}
              </div>
            </CardContent>
            <CardFooter>
              <Button
                type="submit"
                disabled={
                  saving ||
                  !currentPassword ||
                  !newPassword ||
                  newPassword !== confirmPassword
                }
              >
                {saving ? "Updating..." : "Update Password"}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
