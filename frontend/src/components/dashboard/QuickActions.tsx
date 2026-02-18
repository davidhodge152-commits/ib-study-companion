import Link from "next/link";
import { BookOpen, Layers, Upload, MessageCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface QuickActionsProps {
  className?: string;
}

const ACTIONS = [
  {
    href: "/study",
    label: "Study Now",
    icon: BookOpen,
    color: "text-blue-500",
    bg: "bg-blue-500/10 hover:bg-blue-500/20",
  },
  {
    href: "/flashcards",
    label: "Flashcards",
    icon: Layers,
    color: "text-amber-500",
    bg: "bg-amber-500/10 hover:bg-amber-500/20",
  },
  {
    href: "/upload",
    label: "Upload",
    icon: Upload,
    color: "text-emerald-500",
    bg: "bg-emerald-500/10 hover:bg-emerald-500/20",
  },
  {
    href: "/tutor",
    label: "AI Tutor",
    icon: MessageCircle,
    color: "text-rose-500",
    bg: "bg-rose-500/10 hover:bg-rose-500/20",
  },
];

export function QuickActions({ className }: QuickActionsProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {ACTIONS.map(({ href, label, icon: Icon, color, bg }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl p-4 text-center transition-colors",
                bg
              )}
            >
              <Icon className={cn("h-6 w-6", color)} />
              <span className="text-sm font-medium">{label}</span>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
