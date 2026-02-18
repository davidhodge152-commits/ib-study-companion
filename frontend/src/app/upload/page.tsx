"use client";

import { useState, useCallback, useRef } from "react";
import { api } from "@/lib/api-client";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface UploadedFile {
  name: string;
  status: "pending" | "uploading" | "success" | "error";
  progress: number;
  error?: string;
}

export default function UploadPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(async (fileList: FileList | File[]) => {
    const incoming = Array.from(fileList);
    const entries: UploadedFile[] = incoming.map((f) => ({
      name: f.name,
      status: "pending" as const,
      progress: 0,
    }));

    setFiles((prev) => [...prev, ...entries]);

    for (let i = 0; i < incoming.length; i++) {
      const file = incoming[i];
      const idx =
        files.length + i; // approximate index in state

      setFiles((prev) =>
        prev.map((f, j) =>
          j === idx ? { ...f, status: "uploading", progress: 50 } : f
        )
      );

      try {
        const formData = new FormData();
        formData.append("file", file);
        await api.postForm("/api/upload", formData);

        setFiles((prev) =>
          prev.map((f, j) =>
            j === idx ? { ...f, status: "success", progress: 100 } : f
          )
        );
      } catch (err) {
        setFiles((prev) =>
          prev.map((f, j) =>
            j === idx
              ? {
                  ...f,
                  status: "error",
                  progress: 0,
                  error:
                    err instanceof Error ? err.message : "Upload failed",
                }
              : f
          )
        );
      }
    }
  }, [files.length]);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
      e.target.value = "";
    }
  }

  const statusIcon: Record<string, string> = {
    pending: "...",
    uploading: "Uploading",
    success: "Done",
    error: "Failed",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Upload</h1>
        <p className="text-muted-foreground">
          Upload your notes, past papers, and study materials for AI processing
        </p>
      </div>

      {/* Drop Zone */}
      <Card>
        <CardContent className="p-0">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
              isDragging
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50"
            }`}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
              <svg
                className="h-7 w-7 text-muted-foreground"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium">
                Drag and drop files here, or click to browse
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Supports PDF, DOCX, images (PNG, JPG), and text files
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              Browse Files
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
              onChange={handleFileInput}
              className="hidden"
            />
          </div>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {files.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Uploads</CardTitle>
            <CardDescription>
              {files.filter((f) => f.status === "success").length} of{" "}
              {files.length} completed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="divide-y">
              {files.map((file, i) => (
                <li
                  key={`${file.name}-${i}`}
                  className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">{file.name}</p>
                    {file.status === "uploading" && (
                      <div className="mt-1 h-1.5 w-full rounded-full bg-muted">
                        <div
                          className="h-1.5 rounded-full bg-primary transition-all"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    )}
                    {file.error && (
                      <p className="mt-1 text-xs text-destructive">
                        {file.error}
                      </p>
                    )}
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      file.status === "success"
                        ? "text-green-600 dark:text-green-400"
                        : file.status === "error"
                          ? "text-destructive"
                          : "text-muted-foreground"
                    }`}
                  >
                    {statusIcon[file.status]}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
