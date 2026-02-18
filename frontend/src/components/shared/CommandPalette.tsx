"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import {
  LayoutDashboard,
  BookOpen,
  Brain,
  BarChart3,
  Layers,
  Calendar,
  Upload,
  FileText,
  Users,
  Globe,
  GraduationCap,
  User,
  CreditCard,
  Clock,
  ChartBar,
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard, keywords: "home overview stats" },
  { name: "Study", href: "/study", icon: BookOpen, keywords: "practice questions exam" },
  { name: "AI Tutor", href: "/tutor", icon: Brain, keywords: "chat ai help explain" },
  { name: "Insights", href: "/insights", icon: BarChart3, keywords: "grades analytics progress" },
  { name: "Flashcards", href: "/flashcards", icon: Layers, keywords: "review cards spaced repetition" },
  { name: "Planner", href: "/planner", icon: Calendar, keywords: "schedule tasks plan" },
  { name: "Upload", href: "/upload", icon: Upload, keywords: "files documents notes" },
  { name: "Documents", href: "/documents", icon: FileText, keywords: "files notes materials" },
  { name: "Community", href: "/community", icon: Globe, keywords: "posts social share" },
  { name: "Study Groups", href: "/groups", icon: Users, keywords: "collaborate team" },
  { name: "Admissions", href: "/admissions", icon: GraduationCap, keywords: "university college apply" },
  { name: "IB Lifecycle", href: "/lifecycle", icon: Clock, keywords: "timeline milestones journey" },
  { name: "Analytics", href: "/analytics", icon: ChartBar, keywords: "data trends performance" },
  { name: "Account", href: "/account", icon: User, keywords: "profile settings password" },
  { name: "Pricing", href: "/pricing", icon: CreditCard, keywords: "plans subscription billing upgrade" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    []
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages, features..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {NAV_ITEMS.map((item) => (
            <CommandItem
              key={item.href}
              value={`${item.name} ${item.keywords}`}
              onSelect={() => runCommand(() => router.push(item.href))}
            >
              <item.icon className="mr-2 h-4 w-4" />
              {item.name}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
