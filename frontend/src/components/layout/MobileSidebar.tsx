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
  Timer,
  FileEdit,
  Users,
  Newspaper,
  MessageCircle,
  LineChart,
  User,
  CreditCard,
  GraduationCap,
  UserCog,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { SheetClose } from "@/components/ui/sheet";
import { useAuth } from "@/lib/hooks/useAuth";

const ALL_ITEMS = [
  { href: "/dashboard", label: "Command Center", icon: Home, section: "main" },
  { href: "/study", label: "Study", icon: BookOpen, section: "main" },
  { href: "/exam", label: "Exam Mode", icon: Timer, section: "main" },
  { href: "/flashcards", label: "Flashcards", icon: Layers, section: "main" },
  { href: "/upload", label: "Upload", icon: Upload, section: "main" },
  { href: "/documents", label: "Documents", icon: FileText, section: "main" },
  { href: "/insights", label: "Insights", icon: BarChart3, section: "main" },
  { href: "/lifecycle", label: "IB Lifecycle", icon: CalendarCheck, section: "main" },
  { href: "/ia", label: "IA Workspace", icon: FileEdit, section: "main" },
  { href: "/planner", label: "Study Plan", icon: CalendarDays, section: "main" },
  { href: "/groups", label: "Study Groups", icon: Users, section: "social" },
  { href: "/community", label: "Community Papers", icon: Newspaper, section: "social" },
  { href: "/tutor", label: "AI Tutor", icon: MessageCircle, section: "social" },
  { href: "/admissions", label: "Admissions", icon: GraduationCap, section: "social" },
  { href: "/analytics", label: "Analytics", icon: LineChart, section: "social" },
  { href: "/account", label: "Account", icon: User, section: "settings" },
  { href: "/pricing", label: "Pricing", icon: CreditCard, section: "settings" },
  { href: "/parent/settings", label: "Parent Sharing", icon: UserCog, section: "settings" },
];

export function MobileSidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();

  const renderSection = (section: string, title?: string) => (
    <>
      {title && (
        <div className="mt-2 border-t border-border pt-2">
          <p className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {title}
          </p>
        </div>
      )}
      {ALL_ITEMS.filter((i) => i.section === section).map(
        ({ href, label, icon: Icon }) => (
          <SheetClose asChild key={href}>
            <Link
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                pathname === href
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {label}
            </Link>
          </SheetClose>
        )
      )}
    </>
  );

  return (
    <ScrollArea className="h-full">
      <div className="border-b border-border p-5">
        <h1 className="text-lg font-bold">IB Study Companion</h1>
      </div>
      <nav className="space-y-1 p-4" aria-label="Mobile navigation">
        {renderSection("main")}
        {renderSection("social", "Social & AI")}
        {renderSection("settings", "Settings")}

        <div className="mt-2 border-t border-border pt-3">
          <SheetClose asChild>
            <button
              onClick={() => logout()}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
            >
              <LogOut className="h-5 w-5 shrink-0" />
              Log Out
            </button>
          </SheetClose>
        </div>
      </nav>
    </ScrollArea>
  );
}
