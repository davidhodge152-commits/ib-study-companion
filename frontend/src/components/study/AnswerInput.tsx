"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Loader2, Send, Mic, MicOff, Paperclip, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface AnswerInputProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  isGrading: boolean;
  attachments?: File[];
  onAttachmentsChange?: (files: File[]) => void;
  className?: string;
}

export function AnswerInput({
  value,
  onChange,
  onSubmit,
  isGrading,
  attachments = [],
  onAttachmentsChange,
  className,
}: AnswerInputProps) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (value.trim() && !isGrading) {
        onSubmit();
      }
    }
  };

  // Voice input via Web Speech API
  const toggleVoice = useCallback(() => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      return;
    }

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    let finalTranscript = "";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + " ";
        } else {
          interim += transcript;
        }
      }
      onChange(value + finalTranscript + interim);
    };

    recognition.onend = () => {
      setIsListening(false);
      if (finalTranscript) {
        onChange(value + finalTranscript);
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [isListening, value, onChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length > 0 && onAttachmentsChange) {
      onAttachmentsChange([...attachments, ...files]);
    }
    // Reset so the same file can be re-selected
    e.target.value = "";
  };

  const removeAttachment = (index: number) => {
    if (onAttachmentsChange) {
      onAttachmentsChange(attachments.filter((_, i) => i !== index));
    }
  };

  const hasSpeechSupport =
    typeof window !== "undefined" &&
    ("webkitSpeechRecognition" in window || "SpeechRecognition" in window);

  return (
    <div className={cn("space-y-3", className)}>
      <Textarea
        placeholder="Type your answer here..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isGrading}
        className="min-h-32 resize-y"
      />

      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {attachments.map((file, i) => (
            <div
              key={`${file.name}-${i}`}
              className="flex items-center gap-1.5 rounded-lg border bg-muted/50 px-2.5 py-1.5 text-xs"
            >
              <Paperclip className="h-3 w-3 text-muted-foreground" />
              <span className="max-w-32 truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => removeAttachment(i)}
                className="ml-0.5 rounded-sm p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <p className="text-xs text-muted-foreground">
            Press{" "}
            {typeof navigator !== "undefined" &&
            /Mac/.test(navigator.userAgent)
              ? "Cmd"
              : "Ctrl"}
            +Enter to submit
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Voice input button */}
          {hasSpeechSupport && (
            <Button
              type="button"
              variant={isListening ? "destructive" : "outline"}
              size="icon"
              onClick={toggleVoice}
              disabled={isGrading}
              title={isListening ? "Stop recording" : "Voice input"}
            >
              {isListening ? (
                <MicOff className="h-4 w-4" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </Button>
          )}

          {/* File attachment button */}
          {onAttachmentsChange && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.pdf"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={isGrading}
                title="Attach file (image or PDF)"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
            </>
          )}

          <Button
            onClick={onSubmit}
            disabled={!value.trim() || isGrading}
          >
            {isGrading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            {isGrading ? "Grading..." : "Submit Answer"}
          </Button>
        </div>
      </div>
    </div>
  );
}
