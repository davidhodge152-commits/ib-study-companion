"use client";

import { useSubjects, useTopics } from "@/lib/hooks/useStudy";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SubjectSelectorProps {
  selectedSubject: string;
  selectedTopic: string;
  onSelect: (subject: string, topic: string) => void;
  className?: string;
}

export function SubjectSelector({
  selectedSubject,
  selectedTopic,
  onSelect,
  className,
}: SubjectSelectorProps) {
  const { data: subjectsData, isLoading: isLoadingSubjects } = useSubjects();
  const { data: topicsData, isLoading: isLoadingTopics } =
    useTopics(selectedSubject);

  const handleSubjectChange = (subject: string) => {
    onSelect(subject, "");
  };

  const handleTopicChange = (topic: string) => {
    onSelect(selectedSubject, topic);
  };

  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-end", className)}>
      {/* Subject dropdown */}
      <div className="flex-1 space-y-2">
        <label className="text-sm font-medium">Subject</label>
        {isLoadingSubjects ? (
          <Skeleton className="h-9 w-full" />
        ) : (
          <Select value={selectedSubject} onValueChange={handleSubjectChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a subject" />
            </SelectTrigger>
            <SelectContent>
              {subjectsData?.subjects.map((subject) => (
                <SelectItem key={subject} value={subject}>
                  {subject}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Topic dropdown */}
      <div className="flex-1 space-y-2">
        <label className="text-sm font-medium">Topic</label>
        {isLoadingTopics && selectedSubject ? (
          <Skeleton className="h-9 w-full" />
        ) : (
          <Select
            value={selectedTopic}
            onValueChange={handleTopicChange}
            disabled={!selectedSubject}
          >
            <SelectTrigger className="w-full">
              <SelectValue
                placeholder={
                  selectedSubject ? "Select a topic" : "Select a subject first"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {topicsData?.topics.map((topic) => (
                <SelectItem key={topic} value={topic}>
                  {topic}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  );
}
