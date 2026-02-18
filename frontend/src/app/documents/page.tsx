"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";

interface Document {
  id: number;
  name: string;
  type: string;
  created_at: string;
  size_bytes?: number;
  subject?: string;
}

export default function DocumentsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["documents"],
    queryFn: () =>
      api.get<{ documents: Document[] }>("/api/documents"),
    staleTime: 2 * 60 * 1000,
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
          {documents.map((doc) => (
            <Card
              key={doc.id}
              className="transition-shadow hover:shadow-md"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{doc.name}</CardTitle>
                    <CardDescription>
                      {doc.subject && `${doc.subject} -- `}
                      {new Date(doc.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                  <span className="rounded bg-muted px-2 py-1 text-xs font-medium uppercase text-muted-foreground">
                    {typeIcons[doc.type] ?? doc.type.toUpperCase()}
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    Uploaded{" "}
                    {new Date(doc.created_at).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
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
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
