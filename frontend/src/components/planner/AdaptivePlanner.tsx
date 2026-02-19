"use client";

import { useState } from "react";
import { useDailyBriefing } from "@/lib/hooks/useAdaptivePlanner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { DailyBriefingCard } from "./DailyBriefingCard";
import { TaskList } from "./TaskList";
import { SmartPlanView } from "./SmartPlanView";
import { DeadlineManager } from "./DeadlineManager";
import { ReprioritizeDialog } from "./ReprioritizeDialog";
import { RefreshCw } from "lucide-react";

export function AdaptivePlanner() {
  const { data: briefing, isLoading: briefingLoading } = useDailyBriefing();
  const [showReprioritize, setShowReprioritize] = useState(false);

  return (
    <div className="space-y-6">
      {/* Hero: Daily Briefing */}
      <DailyBriefingCard briefing={briefing} isLoading={briefingLoading} />

      {/* Tabs */}
      <Tabs defaultValue="today">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="today">Today</TabsTrigger>
            <TabsTrigger value="week">Week Plan</TabsTrigger>
            <TabsTrigger value="deadlines">Deadlines</TabsTrigger>
          </TabsList>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowReprioritize(true)}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Reprioritize
          </Button>
        </div>

        <TabsContent value="today" className="mt-4">
          <TaskList />
        </TabsContent>

        <TabsContent value="week" className="mt-4">
          <SmartPlanView />
        </TabsContent>

        <TabsContent value="deadlines" className="mt-4">
          <DeadlineManager />
        </TabsContent>
      </Tabs>

      <ReprioritizeDialog
        open={showReprioritize}
        onOpenChange={setShowReprioritize}
      />
    </div>
  );
}
