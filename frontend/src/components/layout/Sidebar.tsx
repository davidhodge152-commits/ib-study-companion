"use client";

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
} from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import { useNotifications } from "@/lib/hooks/useNotifications";
import { ScrollArea } from "@/components/ui/scroll-area";

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
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
        active
          ? "bg-brand-600 text-white"
          : "text-slate-300 hover:bg-slate-800 hover:text-white"
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="h-5 w-5 shrink-0" />
      {label}
      {badge && badge > 0 ? (
        <span className="ml-auto rounded-full bg-violet-500 px-2 py-0.5 text-xs font-bold text-white">
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

  return (
    <aside className="hidden lg:flex w-64 flex-col bg-slate-900 dark:bg-slate-950 text-white fixed h-full z-30">
      {/* Header */}
      <div className="border-b border-slate-700 p-5">
        <h1 className="text-lg font-bold">IB Study Companion</h1>
        {profile && (
          <>
            <p className="mt-1 text-sm text-slate-400">{profile.name}</p>
            <p className="text-xs text-slate-500">{profile.exam_session}</p>
          </>
        )}

        {/* XP & Streak */}
        {gamification && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand-600 text-xs font-bold">
                {gamification.level}
              </span>
              <div className="flex-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">
                    Level {gamification.level}
                  </span>
                  <span className="text-brand-400">
                    {gamification.total_xp} XP
                  </span>
                </div>
                <div className="mt-0.5 h-1.5 w-full rounded-full bg-slate-700">
                  <div
                    className="h-1.5 rounded-full bg-brand-500 transition-all"
                    style={{ width: `${gamification.xp_progress_pct}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <span
                  className={cn(
                    "text-lg",
                    gamification.current_streak > 0
                      ? "animate-pulse"
                      : "opacity-40"
                  )}
                >
                  🔥
                </span>
                <span
                  className={cn(
                    gamification.current_streak > 0
                      ? "font-semibold text-orange-400"
                      : "text-slate-500"
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
                    stroke="#374151"
                    strokeWidth="3"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke={
                      gamification.daily_goal_pct >= 100
                        ? "#22c55e"
                        : "#6366f1"
                    }
                    strokeWidth="3"
                    strokeDasharray={`${gamification.daily_goal_pct}, 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="text-slate-400">
                  {gamification.daily_goal_pct}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1 p-4">
        <nav className="space-y-1" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={pathname === item.href}
            />
          ))}

          <div className="mt-2 border-t border-slate-700 pt-2">
            <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Social
            </p>
          </div>
          {SOCIAL_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={pathname === item.href}
            />
          ))}

          <div className="mt-2 border-t border-slate-700 pt-2">
            <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
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
      <div className="flex items-center justify-between border-t border-slate-700 p-4">
        <div className="flex items-center gap-2">
          <Link
            href="/onboarding"
            className="flex items-center px-3 py-2 text-xs text-slate-500 transition-colors hover:text-slate-300"
          >
            <Settings className="mr-1 h-3 w-3" />
            Edit Profile
          </Link>
          {isAuthenticated && (
            <button
              onClick={() => logout()}
              className="flex items-center px-3 py-2 text-xs text-slate-500 transition-colors hover:text-red-400"
            >
              <LogOut className="mr-1 h-3 w-3" />
              Logout
            </button>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={togglePanel}
            className="relative flex h-[44px] w-[44px] items-center justify-center rounded-lg text-slate-500 transition-colors hover:text-slate-300"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex h-[44px] w-[44px] items-center justify-center rounded-lg text-slate-500 transition-colors hover:text-slate-300"
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
    </aside>
  );
}
