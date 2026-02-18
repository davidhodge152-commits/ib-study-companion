"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Layers, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

interface Document {
  id: number;
  filename: string;
  name?: string;
  doc_type: string;
  type?: string;
  uploaded_at: string;
  created_at?: string;
  size_bytes?: number;
  subject?: string;
  level?: string;
  chunks?: number;
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [generatingId, setGeneratingId] = useState<number | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["documents"],
    queryFn: () =>
      api.get<{ documents: Document[] }>("/api/documents"),
    staleTime: 2 * 60 * 1000,
  });

  const generateFlashcards = useMutation({
    mutationFn: (docId: number) =>
      api.post<{ success: boolean; cards_created: number; subject: string }>(
        "/api/flashcards/generate",
        { document_id: docId, count: 10 }
      ),
    onSuccess: (result) => {
      toast.success(
        `Created ${result.cards_created} flashcards for ${result.subject}!`
      );
      queryClient.invalidateQueries({ queryKey: ["flashcards"] });
      setGeneratingId(null);
    },
    onError: () => {
      toast.error("Failed to generate flashcards. Please try again.");
      setGeneratingId(null);
    },
  });

  if (isLoading) return <LoadingSkeleton variant="card" count={6} />;

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-center">
        <p className="text-destructive">
          Failed to load documents. Please try refreshing.
        </p>
      </div>
    );
  }

  const documents = data?.documents ?? [];

  const typeIcons: Record<string, string> = {
    pdf: "PDF",
    docx: "DOCX",
    image: "IMG",
    text: "TXT",
    past_paper: "EXAM",
    mark_scheme: "MS",
    notes: "NOTES",
    subject_guide: "GUIDE",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Documents</h1>
        <p className="text-muted-foreground">
          View and manage your uploaded study materials
        </p>
      </div>

      {documents.length === 0 ? (
        <EmptyState
          title="No documents yet"
          description="Upload notes, past papers, or textbook excerpts to get started."
          action={
            <a
              href="/upload"
              className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Upload Documents
            </a>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => {
            const displayName = doc.name || doc.filename || "Untitled";
            const displayType = doc.type || doc.doc_type || "file";
            const displayDate = doc.created_at || doc.uploaded_at;
            const isGenerating = generatingId === doc.id;

            return (
              <Card
                key={doc.id}
                className="flex flex-col transition-shadow hover:shadow-md"
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{displayName}</CardTitle>
                      <CardDescription>
                        {doc.subject && `${doc.subject} `}
                        {doc.level && doc.level !== "unknown" && `(${doc.level}) `}
                        {doc.chunks != null && `• ${doc.chunks} chunks`}
                      </CardDescription>
                    </div>
                    <span className="rounded bg-muted px-2 py-1 text-xs font-medium uppercase text-muted-foreground">
                      {typeIcons[displayType] ?? displayType.toUpperCase().replace("_", " ")}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="flex-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      {displayDate
                        ? `Uploaded ${new Date(displayDate).toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })}`
                        : "Upload date unknown"}
                    </span>
                    {doc.size_bytes != null && (
                      <span>
                        {doc.size_bytes < 1024 * 1024
                          ? `${Math.round(doc.size_bytes / 1024)} KB`
                          : `${(doc.size_bytes / (1024 * 1024)).toFixed(1)} MB`}
                      </span>
                    )}
                  </div>
                </CardContent>
                <CardFooter>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    disabled={isGenerating || generateFlashcards.isPending}
                    onClick={() => {
                      setGeneratingId(doc.id);
                      generateFlashcards.mutate(doc.id);
                    }}
                  >
                    {isGenerating ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Layers className="mr-2 h-4 w-4" />
                    )}
                    {isGenerating ? "Generating..." : "Generate Flashcards"}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
