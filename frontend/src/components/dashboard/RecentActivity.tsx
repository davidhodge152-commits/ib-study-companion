import {
  BookOpen,
  Layers,
  Upload,
  Users,
  MessageCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ActivityItem } from "@/lib/types";

interface RecentActivityProps {
  items: ActivityItem[];
  className?: string;
}

const ACTIVITY_ICONS: Record<
  ActivityItem["type"],
  { icon: React.ComponentType<{ className?: string }>; color: string }
> = {
  study: { icon: BookOpen, color: "text-blue-500 bg-blue-500/10" },
  flashcard: { icon: Layers, color: "text-amber-500 bg-amber-500/10" },
  upload: { icon: Upload, color: "text-emerald-500 bg-emerald-500/10" },
  community: { icon: Users, color: "text-violet-500 bg-violet-500/10" },
  tutor: { icon: MessageCircle, color: "text-rose-500 bg-rose-500/10" },
};

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHrs = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHrs / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHrs < 24) return `${diffHrs}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(timestamp).toLocaleDateString();
}

export function RecentActivity({ items, className }: RecentActivityProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No recent activity yet. Start studying to see your progress!
          </p>
        ) : (
          <div className="space-y-4">
            {items.map((item) => {
              const config = ACTIVITY_ICONS[item.type];
              const Icon = config.icon;

              return (
                <div key={item.id} className="flex items-start gap-3">
                  <div
                    className={cn(
                      "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                      config.color
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-snug">{item.description}</p>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {formatRelativeTime(item.timestamp)}
                      </span>
                      {item.subject && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          {item.subject}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
