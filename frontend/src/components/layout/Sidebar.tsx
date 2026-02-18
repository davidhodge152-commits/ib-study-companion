"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  BookOpen,
  Layers,
  Upload,
  FileText,
  BarChart3,
  CalendarCheck,
  CalendarDays,
  Users,
  Newspaper,
  MessageCircle,
  LineChart,
  User,
  CreditCard,
  UserCog,
  Moon,
  Sun,
  Bell,
  LogOut,
  Settings,
  Search,
  GraduationCap,
} from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import { useNotifications } from "@/lib/hooks/useNotifications";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Command Center", icon: Home },
  { href: "/study", label: "Study", icon: BookOpen },
  { href: "/flashcards", label: "Flashcards", icon: Layers },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/insights", label: "Insights", icon: BarChart3 },
  { href: "/lifecycle", label: "IB Lifecycle", icon: CalendarCheck },
  { href: "/planner", label: "Study Plan", icon: CalendarDays },
];

const SOCIAL_ITEMS = [
  { href: "/groups", label: "Study Groups", icon: Users },
  { href: "/community", label: "Community Papers", icon: Newspaper },
  { href: "/tutor", label: "AI Tutor", icon: MessageCircle },
  { href: "/admissions", label: "Admissions", icon: GraduationCap },
  { href: "/analytics", label: "Analytics", icon: LineChart },
];

const SETTINGS_ITEMS = [
  { href: "/account", label: "Account", icon: User },
  { href: "/pricing", label: "Pricing", icon: CreditCard },
  { href: "/parent/settings", label: "Parent Sharing", icon: UserCog },
];

function NavLink({
  href,
  label,
  icon: Icon,
  active,
  badge,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  badge?: number;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150",
        active
          ? "bg-primary text-primary-foreground shadow-sm"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      {label}
      {badge && badge > 0 ? (
        <span className="ml-auto rounded-full bg-destructive px-2 py-0.5 text-[10px] font-bold text-white">
          {badge}
        </span>
      ) : null}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { profile, gamification, logout, isAuthenticated } = useAuth();
  const { unreadCount, togglePanel } = useNotifications();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  return (
    <aside className="hidden lg:flex w-64 flex-col border-r border-border bg-card text-card-foreground fixed h-full z-30">
      {/* Header */}
      <div className="border-b border-border p-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <BookOpen className="h-4 w-4 text-primary-foreground" />
          </div>
          <h1 className="text-base font-bold">IB Study</h1>
        </div>
        {profile && (
          <>
            <p className="mt-2 text-sm font-medium">{profile.name}</p>
            <p className="text-xs text-muted-foreground">{profile.exam_session}</p>
          </>
        )}

        {/* XP & Streak */}
        {gamification ? (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                {gamification.level}
              </span>
              <div className="flex-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    Level {gamification.level}
                  </span>
                  <span className="font-medium text-primary">
                    {gamification.total_xp} XP
                  </span>
                </div>
                <div className="mt-0.5 h-1.5 w-full rounded-full bg-muted">
                  <div
                    className="h-1.5 rounded-full bg-primary transition-all"
                    style={{ width: `${gamification.xp_progress_pct}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <span
                  className={cn(
                    "text-lg leading-none",
                    gamification.current_streak > 0 ? "" : "opacity-40"
                  )}
                >
                  🔥
                </span>
                <span
                  className={cn(
                    gamification.current_streak > 0
                      ? "font-semibold text-orange-500"
                      : "text-muted-foreground"
                  )}
                >
                  {gamification.current_streak} day
                  {gamification.current_streak !== 1 ? "s" : ""}
                </span>
              </div>
              <div
                className="flex items-center gap-1"
                title={`Daily goal: ${gamification.daily_xp_today}/${gamification.daily_goal_xp} XP`}
              >
                <svg className="h-5 w-5" viewBox="0 0 36 36">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    className="stroke-muted"
                    strokeWidth="3"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    className={
                      gamification.daily_goal_pct >= 100
                        ? "stroke-green-500"
                        : "stroke-primary"
                    }
                    strokeWidth="3"
                    strokeDasharray={`${gamification.daily_goal_pct}, 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="text-muted-foreground">
                  {gamification.daily_goal_pct}%
                </span>
              </div>
            </div>
          </div>
        ) : isAuthenticated ? (
          <div className="mt-3 space-y-2" aria-label="Loading gamification stats">
            <div className="flex items-center gap-2">
              <span className="inline-block h-7 w-7 animate-pulse rounded-full bg-muted" />
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="inline-block h-3 w-12 animate-pulse rounded bg-muted" />
                  <span className="inline-block h-3 w-10 animate-pulse rounded bg-muted" />
                </div>
                <div className="h-1.5 w-full animate-pulse rounded-full bg-muted" />
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Search trigger */}
      <div className="px-4 pt-4">
        <button
          onClick={() =>
            document.dispatchEvent(
              new KeyboardEvent("keydown", { key: "k", metaKey: true })
            )
          }
          className="flex w-full items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <Search className="h-4 w-4" />
          <span>Search...</span>
          <kbd className="ml-auto rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 p-4">
        <nav className="space-y-0.5" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={pathname === item.href}
            />
          ))}

          <div className="mt-3 border-t border-border pt-3">
            <p className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Social & AI
            </p>
          </div>
          {SOCIAL_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={pathname === item.href}
            />
          ))}

          <div className="mt-3 border-t border-border pt-3">
            <p className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Settings
            </p>
          </div>
          {SETTINGS_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={pathname === item.href}
            />
          ))}
        </nav>
      </ScrollArea>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-border p-4">
        <div className="flex items-center gap-1">
          <Link
            href="/onboarding"
            className="flex items-center px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground rounded-md hover:bg-accent"
          >
            <Settings className="mr-1.5 h-3.5 w-3.5" />
            Edit Profile
          </Link>
          {isAuthenticated && (
            <button
              onClick={() => setShowLogoutConfirm(true)}
              className="flex items-center px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:text-destructive rounded-md hover:bg-destructive/10"
            >
              <LogOut className="mr-1.5 h-3.5 w-3.5" />
              Logout
            </button>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={togglePanel}
            className="relative flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:text-foreground hover:bg-accent"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute right-0.5 top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:text-foreground hover:bg-accent"
            aria-label="Toggle dark mode"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={showLogoutConfirm}
        onOpenChange={setShowLogoutConfirm}
        title="Log out?"
        description="Are you sure you want to log out? Any unsaved progress will be lost."
        confirmLabel="Log out"
        cancelLabel="Cancel"
        variant="destructive"
        onConfirm={() => logout()}
      />
    </aside>
  );
}
